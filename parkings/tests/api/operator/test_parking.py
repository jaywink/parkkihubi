import datetime
import json

import pytest
from django.conf import settings
from django.core.urlresolvers import reverse
from freezegun import freeze_time

from parkings.models import Parking

from ..utils import ALL_METHODS, check_method_status_codes, check_required_fields, delete, patch, post, put

list_url = reverse('operator:v1:parking-list')


def get_detail_url(obj):
    return reverse('operator:v1:parking-detail', kwargs={'pk': obj.pk})


@pytest.fixture
def new_parking_data():
    return {
        'special_code': 'V',  'device_identifier': 'ea95d137-7496-4ba1-92bd-6e9ac79ebac1', 'zone': 3,
        'registration_number': 'JLH-247',  'time_start': '2016-12-10T20:34:38Z',
        'time_end': '2016-12-10T23:33:29Z', 'resident_code': 'N',
        'location': {'coordinates': [60.16896809536978, 24.942075065834615], 'type': 'Point'},
        'address': {'city': 'Kannus', 'street': 'Litsibulevardi 11', 'postal_code': '75945'}
    }


def check_parking_object(parking_data, parking_obj):
    """
    Compare parking data dict posted the API to the actual Parking object that was created/updated.
    """

    # string valued fields should match 1:1
    for field in {'device_identifier', 'registration_number', 'resident_code', 'special_code', 'zone'}:
        assert parking_data[field] == getattr(parking_obj, field)

    assert parking_data['time_start'] == parking_obj.time_start.strftime('%Y-%m-%dT%H:%M:%SZ')
    assert parking_data['time_end'] == parking_obj.time_end.strftime('%Y-%m-%dT%H:%M:%SZ')
    assert parking_data['location'] == json.loads(parking_obj.location.geojson)

    if parking_obj.address:
        address = parking_obj.address
        assert parking_data['address'] == {
            'city': address.city, 'postal_code': address.postal_code, 'street': address.street
        }
    else:
        assert parking_data['address'] is None


def check_response_parking_data(posted_parking_data, response_parking_data):
    """
    Check that parking data dict in a response has the right fields and matches the posted one.
    """
    expected_keys = {'id', 'special_code', 'device_identifier', 'zone', 'registration_number', 'time_start',
                     'time_end', 'resident_code', 'address', 'location', 'created_at', 'modified_at', 'operator'}

    posted_data_keys = set(posted_parking_data)
    returned_data_keys = set(response_parking_data)
    assert returned_data_keys == expected_keys

    # assert common fields equal
    for key in returned_data_keys & posted_data_keys:
        assert response_parking_data[key] == posted_parking_data[key]


def test_disallowed_methods(operator_api_client, parking):
    list_disallowed_methods = ('get', 'put', 'patch', 'delete')
    check_method_status_codes(operator_api_client, list_url, list_disallowed_methods, 405)

    detail_disallowed_methods = ('get', 'post')
    check_method_status_codes(operator_api_client, get_detail_url(parking), detail_disallowed_methods, 405)


def test_unauthenticated_and_normal_users_cannot_do_anything(api_client, user_api_client, parking):
    urls = (list_url, get_detail_url(parking))
    check_method_status_codes(api_client, urls, ALL_METHODS, 403)
    check_method_status_codes(user_api_client, urls, ALL_METHODS, 403)


def test_parking_required_fields(operator_api_client, parking):
    expected_required_fields = {'registration_number', 'device_identifier', 'location', 'time_start', 'time_end',
                                'zone'}
    check_required_fields(operator_api_client, list_url, expected_required_fields)
    check_required_fields(operator_api_client, get_detail_url(parking), expected_required_fields, detail_endpoint=True)


def test_post_parking(operator_api_client, operator, new_parking_data):
    response_parking_data = post(operator_api_client, list_url, new_parking_data)

    # check data in the response
    check_response_parking_data(new_parking_data, response_parking_data)

    # check the actual object
    new_parking = Parking.objects.get(id=response_parking_data['id'])
    check_parking_object(new_parking_data, new_parking)

    # operator should be autopopulated
    assert new_parking.operator == operator


def test_put_parking(operator_api_client, parking, new_parking_data):
    detail_url = get_detail_url(parking)
    response_parking_data = put(operator_api_client, detail_url, new_parking_data)

    # check data in the response
    check_response_parking_data(new_parking_data, response_parking_data)

    # check the actual object
    parking.refresh_from_db()
    check_parking_object(new_parking_data, parking)


def test_patch_parking(operator_api_client, parking):
    detail_url = get_detail_url(parking)
    new_zone = parking.zone % 3 + 1
    response_parking_data = patch(operator_api_client, detail_url, {'zone': new_zone})

    # check data in the response
    check_response_parking_data({'zone': new_zone}, response_parking_data)

    # check the actual object
    parking.refresh_from_db()
    assert parking.zone == new_zone


def test_delete_parking(operator_api_client, parking):
    detail_url = get_detail_url(parking)
    delete(operator_api_client, detail_url)

    assert not Parking.objects.filter(id=parking.id).exists()


def test_operator_cannot_be_set(operator_api_client, operator, operator_2, new_parking_data):
    new_parking_data['operator'] = str(operator_2.id)

    # POST
    response_parking_data = post(operator_api_client, list_url, new_parking_data)
    new_parking = Parking.objects.get(id=response_parking_data['id'])
    assert new_parking.operator == operator

    # PUT
    detail_url = get_detail_url(new_parking)
    put(operator_api_client, detail_url, new_parking_data)
    new_parking.refresh_from_db()
    assert new_parking.operator == operator

    # PATCH
    patch(operator_api_client, detail_url, {'operator': str(operator_2.id)})
    new_parking.refresh_from_db()
    assert new_parking.operator == operator


def test_cannot_access_other_than_own_parkings(operator_2_api_client, parking, new_parking_data):
    detail_url = get_detail_url(parking)
    put(operator_2_api_client, detail_url, new_parking_data, 403)
    patch(operator_2_api_client, detail_url, new_parking_data, 403)
    delete(operator_2_api_client, detail_url, 403)


def test_cannot_modify_parking_after_modify_period(operator_api_client, new_parking_data):
    start_time = datetime.datetime(2010, 1, 1, 12, 00)

    with freeze_time(start_time):
        response_parking_data = post(operator_api_client, list_url, new_parking_data)

    new_parking = Parking.objects.get(id=response_parking_data['id'])
    new_parking_data['zone'] = 2  # change a value just for the heck of it, should not really matter
    end_time = start_time + settings.PARKINGS_TIME_EDITABLE + datetime.timedelta(minutes=1)

    with freeze_time(end_time):
        put(operator_api_client, get_detail_url(new_parking), new_parking_data, 403)
