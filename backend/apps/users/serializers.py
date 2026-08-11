from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import serializers

User = get_user_model()


class UserSectorMembershipSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    sector = serializers.IntegerField(source="sector_id", read_only=True)
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    sector_code = serializers.CharField(source="sector.code", read_only=True, allow_null=True)
    is_primary = serializers.BooleanField(read_only=True)
    is_manager = serializers.BooleanField(read_only=True)


class CurrentUserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="full_name", read_only=True)
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    permissions = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    sector_memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "name", "first_name", "last_name", "username", "email", "is_active", "is_staff", "groups", "permissions", "photo", "photo_url", "sector_memberships", "last_login", "date_joined")

    def get_permissions(self, obj):
        return sorted(obj.get_all_permissions())

    def get_photo_url(self, obj):
        if not getattr(obj, "photo", None):
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url

    def get_sector_memberships(self, obj):
        memberships = getattr(obj, "active_sector_memberships", None)
        if memberships is None:
            memberships = obj.sector_memberships.filter(active=True).select_related("sector").order_by("-is_primary", "sector__name")
        return UserSectorMembershipSummarySerializer(memberships, many=True).data


class UserSerializer(CurrentUserSerializer):
    group_names = serializers.SlugRelatedField(source="groups", many=True, queryset=Group.objects.all(), slug_field="name", required=False, write_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(source="user_permissions", many=True, queryset=Permission.objects.all(), required=False, write_only=True)

    class Meta(CurrentUserSerializer.Meta):
        fields = CurrentUserSerializer.Meta.fields + ("group_names", "permission_ids")
        read_only_fields = ("id", "permissions", "photo_url", "last_login", "date_joined", "is_staff")

    def create(self, validated_data):
        groups = validated_data.pop("groups", [])
        permissions = validated_data.pop("user_permissions", [])
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        user.groups.set(groups)
        user.user_permissions.set(permissions)
        return user


class UserCreateSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("password",)
