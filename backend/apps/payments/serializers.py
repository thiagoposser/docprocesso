from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.sectors.policies import can_access_sector
from apps.documents.models import validate_document_file
from apps.documents.serializers import AttachmentSerializer

from .models import Payment, PaymentMethod, PaymentReceipt, Supplier
from .services import InvalidPaymentTransition, PaymentAccessDenied, create_payment, save_payment, save_supplier


def mask_tax_id(value):
    return f"***{value[-4:]}" if value else ""


class SupplierSerializer(serializers.ModelSerializer):
    tax_id = serializers.CharField(write_only=True)
    tax_id_masked = serializers.SerializerMethodField()
    bank_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    bank_branch = serializers.CharField(write_only=True, required=False, allow_blank=True)
    bank_account = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Supplier
        fields = ("id", "name", "tax_id", "tax_id_masked", "email", "phone", "bank_name", "bank_branch", "bank_account", "active", "created_at", "updated_at")
        read_only_fields = ("id", "tax_id_masked", "created_at", "updated_at")

    def get_tax_id_masked(self, obj):
        return mask_tax_id(obj.tax_id)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = self.context["request"].user
        if user.has_perm("payments.view_financial_data"):
            data.update(tax_id=instance.tax_id, bank_name=instance.bank_name, bank_branch=instance.bank_branch, bank_account=instance.bank_account)
        else:
            data.pop("email", None)
            data.pop("phone", None)
        return data

    def create(self, validated_data):
        try:
            return save_supplier(Supplier(), **validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error

    def update(self, instance, validated_data):
        try:
            return save_supplier(instance, **validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error


class PaymentSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    process_number = serializers.CharField(source="process.number", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    protected_fields = {"status", "scheduled_at", "paid_at", "paid_amount", "payment_method", "paid_by", "cancelled_at", "cancellation_reason", "created_by"}

    class Meta:
        model = Payment
        fields = (
            "id", "process", "process_number", "document", "sector", "sector_name", "supplier", "supplier_name",
            "workflow_version", "stage",
            "description", "amount", "due_date", "status", "is_overdue", "scheduled_at", "paid_at", "paid_amount",
            "payment_method", "paid_by", "cancelled_at", "cancellation_reason", "created_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "process_number", "sector_name", "supplier_name", "workflow_version", "stage", "status", "is_overdue", "scheduled_at", "paid_at", "paid_amount", "payment_method", "paid_by", "cancelled_at", "cancellation_reason", "created_by", "created_at", "updated_at")

    def to_internal_value(self, data):
        attempted = self.protected_fields.intersection(data)
        if attempted:
            raise serializers.ValidationError({field: "Este campo só pode ser alterado por uma ação financeira." for field in sorted(attempted)})
        return super().to_internal_value(data)

    def validate(self, attrs):
        process = attrs.get("process", getattr(self.instance, "process", None))
        sector = attrs.get("sector", getattr(self.instance, "sector", None))
        if process and sector and sector != (process.current_sector or process.origin_sector):
            raise serializers.ValidationError({"sector": "O setor do pagamento deve ser o setor atual do processo."})
        request = self.context["request"]
        permission = "payments.add_payment" if self.instance is None else "payments.change_payment"
        if sector and not can_access_sector(request.user, permission=permission, sector=sector):
            raise serializers.ValidationError({"sector": "Você não possui acesso financeiro a este setor."})
        if process and not can_access_sector(
            request.user, permission="processes.view_administrativeprocess",
            sector=process.current_sector or process.origin_sector,
        ):
            raise serializers.ValidationError({"process": "Processo não encontrado ou fora do seu escopo."})
        return attrs

    def create(self, validated_data):
        try:
            return create_payment(actor=self.context["request"].user, **validated_data)
        except (PaymentAccessDenied, InvalidPaymentTransition) as error:
            raise serializers.ValidationError({"process": str(error)}) from error
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error

    def update(self, instance, validated_data):
        try:
            return save_payment(instance, **validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict) from error


class PaymentScheduleSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField()

    def validate_scheduled_at(self, value):
        from django.utils import timezone
        if value <= timezone.now():
            raise serializers.ValidationError("O agendamento deve estar no futuro.")
        return value


class PaymentConfirmSerializer(serializers.Serializer):
    paid_at = serializers.DateTimeField()
    paid_amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices)

    def validate_paid_at(self, value):
        from django.utils import timezone
        if value > timezone.now():
            raise serializers.ValidationError("A data do pagamento não pode estar no futuro.")
        return value


class PaymentCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(trim_whitespace=True, allow_blank=False, max_length=2000)


class PaymentReceiptSerializer(serializers.ModelSerializer):
    attachment = AttachmentSerializer(read_only=True)

    class Meta:
        model = PaymentReceipt
        fields = ("id", "payment", "attachment", "created_by", "created_at")
        read_only_fields = fields


class PaymentReceiptUploadSerializer(serializers.Serializer):
    file = serializers.FileField(validators=[validate_document_file])
