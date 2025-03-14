from iss_tracker import norm, current_epoch
import requests
import math as m
import time

BASE_URL = "http://localhost:5000"

def test_norm():
    assert norm(1,1,1) == m.sqrt(3)
    assert norm(0,1,0) == 1
    assert norm(0,0,0) == 0
    assert isinstance(norm(1,2,3),float) == True

def test_norm_invalid_inputs():
    assert norm("a", 1, 2) is None
    assert norm(None, 1, 2) is None
    assert norm(1, [2], 3) is None

def test_current_epoch():
    current_time = time.mktime(time.gmtime())
    keys = [
        time.strftime('%Y-%jT%H:%M:%S.000Z', time.gmtime(current_time - 60)),
        time.strftime('%Y-%jT%H:%M:%S.000Z', time.gmtime(current_time + 60)),
        time.strftime('%Y-%jT%H:%M:%S.000Z', time.gmtime(current_time))
    ]
    closest = current_epoch(keys)
    assert closest == time.strftime('%Y-%jT%H:%M:%S.000Z', time.gmtime(current_time))

def test_current_epoch_empty_list():
    assert current_epoch([]) is None

def test_current_epoch_single_key():
    key = time.strftime('%Y-%jT%H:%M:%S.000Z', time.gmtime())
    assert current_epoch([key]) == key
    
def test_get_epochs():
    response = requests.get(f'{BASE_URL}/epochs')
    assert response.status_code == 200

def test_get_epochs_with_params():
    response = requests.get(f'{BASE_URL}/epochs?limit=5&offset=10')
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 5

def test_get_epochs_invalid_params():
    response = requests.get(f'{BASE_URL}/epochs?limit=abc&offset=xyz')
    assert response.status_code == 200  

def test_invalid_endpoint():
    response = requests.get(f'{BASE_URL}/invalid_endpoint')
    assert response.status_code == 404

def test_get_now():
    response = requests.get(f'{BASE_URL}/now')
    assert response.status_code == 200

def test_get_epoch_data():
    response = requests.get(f'{BASE_URL}/epochs/2025-999T00:00:00.000Z')
    assert response.status_code == 404
    
def test_get_epoch_speed():
    response = requests.get(f'{BASE_URL}/epochs/2025-999T00:00:00.000Z/speed')
    assert response.status_code == 404


