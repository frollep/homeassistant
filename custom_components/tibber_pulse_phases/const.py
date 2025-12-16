"""Constants for Tibber Pulse Phases."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "tibber_pulse_phases"
PLATFORMS = [Platform.SENSOR]
CONF_TOKEN = "token"
CONF_HOME_ID = "home_id"
CONF_HOME_NAME = "home_name"

HTTP_URL = "https://api.tibber.com/v1-beta/gql"
WS_URL = "wss://api.tibber.com/v1-beta/gql"

SUBSCRIPTION_QUERY = """
subscription LiveMeasurement($homeId: ID!) {
  liveMeasurement(homeId: $homeId) {
    timestamp
    power
    powerProduction
    powerPhase1
    powerPhase2
    powerPhase3
    accumulatedConsumption
    accumulatedProduction
    netConsumption
    netProduction
    minPower
    maxPower
    minPowerProduction
    maxPowerProduction
    currentL1
    currentL2
    currentL3
    voltagePhase1
    voltagePhase2
    voltagePhase3
    powerFactor
    signalStrength
  }
}
"""
