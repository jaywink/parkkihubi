from django.conf import settings
from django.db import transaction
from django.utils.timezone import now
from rest_framework import mixins, permissions, serializers, viewsets

from parkings.models import Address, Operator, Parking


class OperatorAPIAddressSerializer(serializers.ModelSerializer):
    city = serializers.CharField(required=True)
    postal_code = serializers.CharField(required=True)
    street = serializers.CharField(required=True)

    class Meta:
        model = Address
        fields = ('city', 'postal_code', 'street')


class OperatorAPIParkingSerializer(serializers.ModelSerializer):
    address = OperatorAPIAddressSerializer(allow_null=True, required=False)

    class Meta:
        model = Parking
        fields = '__all__'
        read_only_fields = ('operator',)

    @transaction.atomic
    def create(self, validated_data):
        address_data = validated_data.pop('address', None)

        if address_data:
            validated_data['address'], _ = Address.objects.get_or_create(
                city=address_data['city'],
                postal_code=address_data['postal_code'],
                street=address_data['street'],
            )

        return Parking.objects.create(**validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        address_data = validated_data.get('address')

        if address_data:
            validated_data['address'], _ = Address.objects.get_or_create(
                city=address_data['city'],
                postal_code=address_data['postal_code'],
                street=address_data['street'],
            )

        for attr, value in validated_data.items():
            # does not handle many-to-many fields
            setattr(instance, attr, value)

        instance.save()
        return instance


class OperatorAPIParkingPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        """
        Allow only operators to create a parking.
        """
        user = request.user

        if not user.is_authenticated():
            return False

        try:
            user.operator
            return True
        except Operator.DoesNotExist:
            pass

        return False

    def has_object_permission(self, request, view, obj):
        """
        Allow only operators to modify and only their own parkings and
        only for a fixed period of time after creation.
        """
        return request.user.operator == obj.operator and (now() - obj.created_at) <= settings.PARKINGS_TIME_EDITABLE


class OperatorAPIParkingViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                                viewsets.GenericViewSet):
    queryset = Parking.objects.all()
    serializer_class = OperatorAPIParkingSerializer
    permission_classes = (OperatorAPIParkingPermission,)

    def perform_create(self, serializer):
        serializer.save(operator=self.request.user.operator)
