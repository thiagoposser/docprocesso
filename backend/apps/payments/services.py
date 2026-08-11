from django.db import transaction


@transaction.atomic
def save_supplier(instance, **values):
    for field, value in values.items():
        setattr(instance, field, value)
    instance.save()
    return instance


@transaction.atomic
def save_payment(instance, **values):
    for field, value in values.items():
        setattr(instance, field, value)
    instance.save()
    return instance
