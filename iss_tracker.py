#!/usr/bin/env python3
import xmltodict
import requests
import logging
import argparse
import socket
import math as m
import time
import json
import redis
from datetime import datetime
from flask import Flask, request
from astropy import coordinates
from astropy import units
from astropy.time import Time
from geopy.geocoders import Nominatim

parser = argparse.ArgumentParser()
parser.add_argument('-l', '--loglevel', type=str, required=False, default='WARNING',
                    help='set log level to DEBUG, INFO, WARNING, ERROR, or CRITICAL')
args = parser.parse_args()
logging.basicConfig(level=args.loglevel)

app = Flask(__name__)
try:
    rd = redis.Redis(host='redis-db', port=6379, db=0)
except redis.ConnectionError as e:
    logging.error('Failed to connect to Redis: %s', e)
    
    
def get_data():
    """
    gets the ISS data when called and stores in redis database

    Args: N/A

    Returns:
        N/A
    """
    try:
        response = requests.get(url='https://nasa-public-data.s3.amazonaws.com/iss-coords/current/ISS_OEM/ISS.OEM_J2K_EPH.xml')
        response.raise_for_status()
        data = xmltodict.parse(response.content)
        state_vectors = data['ndm']['oem']['body']['segment']['data']['stateVector']
        logging.info('Data successfully retrieved')
        if not rd.keys()
            for vector in state_vectors:
                rd.set(vector['EPOCH'], json.dumps(vector))
    except requests.exceptions.RequestException as e:
        logging.error(f'Failed to retrieve data: {e}')
    except (xmltodict.expat.ExpatError, KeyError) as e:
        logging.error(f'Error parsing data: {e}')
    except redis.RedisError as e:
        logging.error('Redis error: %s', e)
    except Exception as e:
        logging.error(f'Unexpected error: {e}')

def norm(x: float,y: float,z: float) -> float:
    """
    Returns the norm of a 3d vector

    Args:
        x (float): x componenet of vector
        y (float): y componenet of vector
        z (float): z componenet of vector
 
    Returns:
        norm (float): norm of vector
    """
    try:
        return m.sqrt(x*x+y*y+z*z) 
    except (TypeError,ValueError):
        logging.error('Invalud input: x, y, and z must be numeric')
        return None
    
def current_epoch(list_of_keys: list[str]) -> dict:
    """
    Finds the epoch from the list of keys that is closest
    to the current time

    Args:
        list_of_keys (list): list of epoch keys
 
    Returns:
        key (string): the key for the closest epoch
    """
    if not list_of_keys:
        logging.error('Empty key list provided')
        return None

    current_time = time.mktime(time.gmtime())
    logging.debug(current_time)
    closest = None
    best = float("inf")
    for key in list_of_keys:
        try:
            check_time = time.mktime(time.strptime(key,'%Y-%jT%H:%M:%S.%fZ'))
            if abs(check_time-current_time) < best:
                best = abs(check_time-current_time)
                closest = key
                logging.debug(best)
        except (ValueError, TypeError):
            logging.error('Invalid key format: %s', key)
    return(closest)

@app.route('/now', methods=['GET'])
def get_now():
    """
    Returns the epoch data closest to the current time

    Args:
        N/A

    Returns:
        Dictionary of epoch data
    """
    try:
        sorted_keys = sorted(k.decode("utf-8") for k in rd.keys("*"))
        if not sorted_keys:
            return {'error': 'No epochs found'}, 404
        
        epoch = current_epoch(sorted_keys)
        if epoch is None:
            return {'error': 'No valid epochs found'}, 500
    
        data = json.loads(rd.get(epoch))
   
        x = float(data['X']['#text']) 
        y = float(data['Y']['#text'])
        z = float(data['Z']['#text'])
    
        epoch_vel_x = float(data['X_DOT']['#text'])
        epoch_vel_y = float(data['Y_DOT']['#text'])
        epoch_vel_z = float(data['Z_DOT']['#text'])

        current_vel = norm(epoch_vel_x,epoch_vel_y,epoch_vel_z)

        this_epoch=time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(data['EPOCH'][:-5], '%Y-%jT%H:%M:%S'))
        cartrep = coordinates.CartesianRepresentation([x, y, z], unit=units.km)
        gcrs = coordinates.GCRS(cartrep, obstime=this_epoch)
        itrs = gcrs.transform_to(coordinates.ITRS(obstime=this_epoch))
        loc = coordinates.EarthLocation(*itrs.cartesian.xyz)

        geocoder = Nominatim(user_agent='iss_tracker')
        geoloc = geocoder.reverse((str(loc.lat.value),str(loc.lon.value)), zoom = 15, language = 'en_US')
    
        if geoloc == None:
            geoloc = 'Not near any cities, likely over an ocean'
        else:
            geoloc = geoloc.address

        data["Instantaneous Velocity"] = {
            "#text": str(current_vel),
            "@units": "km/s"
        }
        
        data["Latitude"] = {
            "#text": str(loc.lat.value),
            "@units": "degrees"
        }
        data["Longitude"] = {
            "#text": str(loc.lon.value),
            "@units": "degrees"
        }
        
        data["Nearest Location"] = {
            "#text":geoloc,
            "@units": "N/A"
        }
        
        return data
    
    except(ValueError, KeyError) as e:
        logging.error('Error fetching current epoch data: %s', e)
        return{'error': 'Internal server error'}, 500

@app.route('/epochs', methods=['GET'])
def get_epochs():
    """
    Returns all epochs

    Args:
        N/A

    Returns:
        List of dicts in json format
    """
    sorted_keys = sorted(k.decode("utf-8") for k in rd.keys("*"))
    
    limit = request.args.get('limit', default=None, type=int)
    offset = request.args.get('offset', default=0, type=int) 
    
    result = sorted_keys[offset:]
    if limit is not None:
        result = result[:limit]
    
    dict_list = [json.loads(rd.get(key)) for key in result if rd.get(key)]

    return dict_list

@app.route('/epochs/<epoch>', methods=['GET'])
def get_epoch_data(epoch):
    """
    Returns the epoch data that matches the requested epoch

    Args:
        epoch (str): The epoch time string requested

    Returns:
        dict: The epoch data dictionary if found, otherwise error message
    """

    data = rd.get(epoch)
    if data is None:
        return {'error': 'Epoch not found'}, 404
    return json.loads(data)


@app.route('/epochs/<epoch>/speed', methods=['GET'])
def get_epoch_speed(epoch):
    """
    Returns the instantaneous speed of the ISS at the requested epoch

    Args:
        epoch (str): The epoch time string requested

    Returns:
        dict: JSON object containing the epoch and its speed in km/s
    """
    try:
        data = rd.get(epoch)
        if data is None:
            return {'error': 'Epoch not found'}, 404
        vector = json.loads(data)
        vel_x = float(vector['X_DOT']['#text'])
        vel_y = float(vector['Y_DOT']['#text'])
        vel_z = float(vector['Z_DOT']['#text'])
        speed = norm(vel_x, vel_y, vel_z)
        return {'Epoch': epoch, 'Instantaneous speed (km/s)': speed}
    except (ValueError, KeyError) as e:
        logging.error(f'Error fetching speed data: {e}')
        return {'error': 'Internal server error'}, 500

@app.route('/epochs/<epoch>/location', methods=['GET'])
def get_epoch_location(epoch):
    """Finds the nearest location to the ISS

    Args:
        epoch (str): Key string to the epoch of interest

    Returns:
        string: String description of location
    """
    try: 
        vector = json.loads(rd.get(epoch))
        x = float(vector['X']['#text'])
        y = float(vector['Y']['#text'])
        z = float(vector['Z']['#text'])
            
        this_epoch=time.strftime('%Y-%m-%d %H:%M:%S', time.strptime(vector['EPOCH'][:-5], '%Y-%jT%H:%M:%S'))

        cartrep = coordinates.CartesianRepresentation([x, y, z], unit=units.km)
        gcrs = coordinates.GCRS(cartrep, obstime=this_epoch)
        itrs = gcrs.transform_to(coordinates.ITRS(obstime=this_epoch))
        loc = coordinates.EarthLocation(*itrs.cartesian.xyz)

        geocoder = Nominatim(user_agent='iss_tracker')
        geoloc = geocoder.reverse((str(loc.lat.value),str(loc.lon.value)), zoom = 15, language = 'en_US')
            
        if geoloc == None:
            geoloc = 'Not near any cities, likely over an ocean'
        else:
            geoloc = geoloc.address
        return {
                "Epoch":epoch,
                "Latitude (deg)":loc.lat.value, 
                "Longitude (deg)":loc.lon.value, 
                "Height (km)":loc.height.value,
                "Nearest Location":geoloc
        }
    except(TypeError, ValueError, AttributeError, IndexError):
        logging.error('Error fetching location data')
        return {"error": "Epoch not found"}, 404

if __name__ == '__main__':
    get_data()
    app.run(debug=True, host='0.0.0.0')
