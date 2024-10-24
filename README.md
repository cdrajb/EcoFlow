# EcoFlow
EcoFlow open API code to get readings the EcoFlow endpoint (for Europe this is https://api-e.ecoflow.com) via mqtt and write to Influx

Credit to Mark Hicks https://github.com/Mark-Hicks/ecoflow-api-examples for the code used to build this

https://developer-eu.ecoflow.com/us/document/powerStreamMicroInverter

You'll need a developer account to get the keys, and to create a subfolder 'include' - create a file in that with the credentials.

MQTT updates every 2 seconds or so, as long as there is sufficient solar to power up the inverter.

There are multiple temperature sensors in the device (see the http API values), but only espTempsensor is sent via MQTT (I assume this is an ESP32 - but in my experience this seems to match the others anyway).
