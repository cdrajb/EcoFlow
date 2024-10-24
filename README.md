# EcoFlow
EcoFlow open API code to get readings for the PowerStream micro inverter from the EcoFlow endpoint (for Europe this is https://api-e.ecoflow.com) via mqtt and write to Influx

Credit to Mark Hicks https://github.com/Mark-Hicks/ecoflow-api-examples for the code used to build this

https://developer-eu.ecoflow.com/us/document/powerStreamMicroInverter

You'll need a developer account to get the keys.
You also need to create a subfolder 'include' - create a file called mqtt_creds_config.py in that with the credentials (see sample file provided).

MQTT updates every 2 seconds or so, as long as there is sufficient solar to power up the inverter.

MQTT does not send all the sensor data (see the http API values); for instance there are multiple temperature sensors in the device, but only espTempsensor is sent via MQTT 
(I assume this is an ESP32 - but in my experience the readings seem to match the others anyway)
