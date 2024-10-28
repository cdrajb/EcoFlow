"""
code to use the Ecoflow Open API to collect mqtt and write a subset to Influx
- Login to API over HTTP using access and secret keys
- Obtain MQTT credentials via HTTP
- Connect to MQTT using obtained credentials
- Subscribe to /quota topic for a device (uses serial number)
- Write selected readings to Influx

Credit to Mark Hicks for the example code built on here https://github.com/Mark-Hicks/ecoflow-api-examples
"""

import hashlib
import hmac
import logging
import random
import ssl
import time
import datetime
import calendar
import json
import sys
import paho.mqtt.client as mqtt
import requests
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.domain.write_precision import WritePrecision
from include import mqtt_creds_config

# Get the keys and device serial number
key = mqtt_creds_config.ecoflowKey
secret = mqtt_creds_config.ecoflowSecret
sn = mqtt_creds_config.ecoflowSN

measures={}
#logging.basicConfig(level=logging.INFO,filename="/home/pi/log/EcoFlow.log",filemode="a", style='{', datefmt='%Y-%m-%d %H:%M:%S', format='{asctime} {levelname} {filename}:{lineno}: {message}')
logging.basicConfig(level=logging.INFO,filename="ecoflow.log",filemode="a", style='{', datefmt='%Y-%m-%d %H:%M:%S', format='{asctime} {levelname} {filename}:{lineno}: {message}')
logging.info("Starting...")

def opendb():
    global db_client
    db_client = InfluxDBClient(url=mqtt_creds_config.influxurl, token=mqtt_creds_config.influxToken, org=mqtt_creds_config.influxOrg, debug=False) # Influx 2.x
# We're writing to the EcoFlow bucket

class MqttClient:
    def __init__(self, url, port, name, user, pwd):
        logging.debug(f"MqttClient: {url}:{port} as {name}")
        self.url = url
        self.port = port
        self.name = name
        self.user = user
        self.pwd = pwd
        self.mqtt = mqtt.Client(name)
        # for paho mqtt v2, this will fail; instead you can use mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, name)
        self.resp = None

    def on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            logging.error(f"MQTT Connect: Response Code = {rc}")

    def on_message(self, client, userdata, msg):
#        logging.info("Received message on topic %s: %s", msg.topic, msg.payload)
        decoded_message=str(msg.payload.decode("utf-8"))
        message=json.loads(decoded_message)
        params=message['param']
        if 'invOutputWatts' in params:
            measures.update({"inv_OP_W": params['invOutputWatts']/10})
        if 'pv1InputWatts' in params:
            measures.update({"PV1_W": params['pv1InputWatts']/10})
        if 'pv2InputWatts' in params:
            measures.update({"PV2_W": params['pv2InputWatts']/10})
        if 'pv1OpVolt' in params:
            measures.update({"PV1_V": params['pv1OpVolt']/100})
        if 'pv2OpVolt' in params:
            measures.update({"PV2_V": params['pv2OpVolt']/100})
        if 'espTempsensor' in params:
            measures.update({"Inv_temp": params['espTempsensor']})
#        timestamp=datetime.datetime.now().strftime("%H:%M")
        self.resp = msg.payload

    def connect(self):
        logging.info(f"MQTT Connect: {self.url}:{self.port}...")
        try:
            self.mqtt.on_connect = self.on_connect
            self.mqtt.on_message = self.on_message
            self.mqtt.tls_set(cert_reqs=ssl.CERT_NONE)
            self.mqtt.username_pw_set(username=self.user, password=self.pwd)
            self.mqtt.connect(self.url, self.port, 60)
            self.mqtt.loop_start()
        except ssl.SSLError as e:
            logging.error(f"MQTT Connect: SSL - {e}")
        except Exception as e:
            logging.error(f"MQTT Connect: Unexpected - {e}")

    def disconnect(self):
        try:
            self.mqtt.loop_stop()
            self.mqtt.disconnect()
        except Exception as e:
            logging.error(f"MQTT Disconnect: Unexpected - {e}")

    def subscribe(self, topic):
        logging.debug(f"MQTT Subscribe: {topic}")
        try:
            self.mqtt.subscribe(topic)
        except Exception as e:
            logging.error(f"MQTT Subscribe: Unexpected - {e}")

    def unsubscribe(self, topic):
        logging.debug(f"MQTT UnSubscribe: {topic}")
        try:
            self.mqtt.unsubscribe(topic)
        except Exception as e:
            logging.error(f"MQTT UnSubscribe: Unexpected - {e}")

    def publish(self, topic, payload):
        logging.debug(f"MQTT Publish: {topic}")
        logging.debug(f"MQTT Publish: payload {payload}")
        try:
            self.mqtt.publish(topic, payload)
        except Exception as e:
            logging.error(f"MQTT Publish: Unexpected - {e}")


def hmac_sha256(data, key):
    hashed = hmac.new(
        key.encode("utf-8"), data.encode("utf-8"), hashlib.sha256
    ).digest()
    return "".join(format(byte, "02x") for byte in hashed)


def get_qstring(params):
    return "&".join([f"{key}={params[key]}" for key in sorted(params.keys())])


def get_api(url, key, secret, params=None):
    nonce = str(random.randint(100000, 999999))
    timestamp = str(int(time.time() * 1000))
    headers = {"accessKey": key, "nonce": nonce, "timestamp": timestamp}
    sign_str = (get_qstring(params) + "&" if params else "") + get_qstring(headers)
    headers["sign"] = hmac_sha256(sign_str, secret)
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"get_api: {response.text}")


if __name__ == "__main__":


    opendb()
    logging.info("connection made to %s, %s", mqtt_creds_config.influxurl, mqtt_creds_config.influxOrg)

    url = "https://api-e.ecoflow.com"
    # Note: In the US use:
    # url = "https://api-a.ecoflow.com"
    path = "/iot-open/sign/certification"


    payload = get_api(f"{url}{path}", key, secret, {"sn": sn})
    data = payload.get("data")

    if data:
        logging.debug("MQTT = %s", data)
        m_url = data["url"]
        port = int(data["port"])
        user = data["certificateAccount"]
        pwd = data["certificatePassword"]
        topic = f"/open/{user}/{sn}/quota"

        mqtt_client = MqttClient(m_url, port, f"test_{user}", user, pwd)
        mqtt_client.connect()
        mqtt_client.subscribe(topic)

        try:
            while True:
                time.sleep(1)
                now = datetime.datetime.now()
                nowtime=now.strftime('%Y-%m-%d %H:%M:%S')
                gmt = time.gmtime()
                ts = calendar.timegm(gmt)
                if len(measures)!=0:
                    payload = {
                      "measurement": "EcoFlow",
                      "fields": measures,
                      "timestamp": ts,
                      "device": "PowerStream"
                    }
                    point = Point.from_dict(payload, write_precision=WritePrecision.S, record_measurement_key="measurement", record_time_key="timestamp", record_tag_keys=["device"])
                    #print(nowtime, point)
                    write_api = db_client.write_api(write_options=SYNCHRONOUS)
                    try:
                        write_api.write(bucket="EcoFlow", record=point)
                        logging.info("%s Written to InfluxDB",len(measures))
                    except Exception as Ex:
                        logging.error(" error writing to database: %s",str(Ex))
                        sys.exit(1)

                    measures={}
 
        except KeyboardInterrupt:
            logging.info("Interrupted - Exiting...")
        except Exception as e:
            logging.error(e)
        mqtt_client.disconnect()

    else:
        logging.error("No MQTT Credentials returned!")
