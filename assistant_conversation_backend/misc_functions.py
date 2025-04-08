import os
import aiohttp
import asyncio
import ssl

HOME_ASSISTANT_TOKEN = os.environ['HOME_ASSISTANT_TOKEN']
HOME_ASSISTANT_URL = os.environ['HOME_ASSISTANT_URL']


async def get_dashboard_summary():
    """
    Fetches Home Assistant states from the API and extracts key information
    to build a dashboard summary.
    
    Returns:
        A string containing a formatted dashboard summary.
    """
    states_url = f"{HOME_ASSISTANT_URL}/states"
    shopping_list_url = f"{HOME_ASSISTANT_URL}/shopping_list"
    headers = {
        "Authorization": f"Bearer {HOME_ASSISTANT_TOKEN}"
    }
    
    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    states = []
    shopping_list_items = []
    
    try:
        async with aiohttp.ClientSession() as session:
            # Fetch states
            async with session.get(states_url, headers=headers, ssl=ssl_context) as response:
                response.raise_for_status()
                states = await response.json()
            
            # Fetch shopping list
            async with session.get(shopping_list_url, headers=headers, ssl=ssl_context) as response:
                response.raise_for_status()
                shopping_list_items = await response.json()
    except aiohttp.ClientError as err:
        return f"Error fetching data: {err}"
    
    # Create a mapping of entity_id to state for easy lookup.
    state_dict = {item["entity_id"]: item for item in states}
    
    lines = []
    
    # Add a title for the dashboard
    lines.append("# Home Assistant Dashboard Summary")
    lines.append("")
    
    # Home Presence & Location
    person = state_dict.get("person.samuel", {})
    person_state = person.get("state", "unknown")
    person_name = person.get("attributes", {}).get("friendly_name", "Unknown")
    
    geocoded = state_dict.get("sensor.fp3_geocoded_location", {})
    geocoded_loc = geocoded.get("state", "N/A")
    
    lines.append("### Home Presence & Location")
    lines.append(f"- **Person:** {person_name} is {person_state}.")
    lines.append(f"- **Geocoded Location:** {geocoded_loc}.")
    lines.append("")
    
    # Device Statuses
    lines.append("### Device Statuses")
    # FP3 (Smartphone) Details
    fp3_battery = state_dict.get("sensor.fp3_battery_level", {}).get("state", "N/A")
    fp3_activity = state_dict.get("sensor.fp3_detected_activity", {}).get("state", "N/A")
    fp3_sleep = state_dict.get("sensor.fp3_sleep_confidence", {}).get("state", "N/A")
    fp3_os = state_dict.get("sensor.fp3_os_version", {}).get("state", "N/A")
    fp3_patch = state_dict.get("sensor.fp3_security_patch", {}).get("state", "N/A")
    
    lines.append("**FP3 (Smartphone)**")
    lines.append(f"- **Battery:** {fp3_battery}%")
    lines.append(f"- **Detected Activity:** {fp3_activity}.")
    lines.append(f"- **Sleep Confidence:** {fp3_sleep}%.")
    lines.append(f"- **OS Version:** {fp3_os}; Security Patch: {fp3_patch}.")
    lines.append("")
    
    # MacBook Air Details
    mac_battery = state_dict.get("sensor.samuels_macbook_air_internal_battery_level", {}).get("state", "N/A")
    mac_storage = state_dict.get("sensor.samuels_macbook_air_storage", {}).get("state", "N/A")
    mac_ssid = state_dict.get("sensor.samuels_macbook_air_ssid", {}).get("state", "N/A")
    
    lines.append("**Samuel’s MacBook Air**")
    lines.append(f"- **Battery Level:** {mac_battery}%")
    lines.append(f"- **Storage Available:** {mac_storage} (percentage available).")
    lines.append(f"- **Connection:** {mac_ssid} (SSID).")
    lines.append("")
    
    # Shopping List Section
    lines.append("### Shopping List")
    if shopping_list_items:
        active_items = [item for item in shopping_list_items if not item.get("complete", False)]
        completed_items = [item for item in shopping_list_items if item.get("complete", False)]
        
        if active_items:
            lines.append("**Items to buy:**")
            for item in active_items:
                lines.append(f"- {item.get('name', 'Unknown item')}")
        else:
            lines.append("No items to buy.")
            
        if completed_items:
            lines.append("\n**Completed items:**")
            for item in completed_items[:5]:  # Limit to 5 most recent completed items
                lines.append(f"- {item.get('name', 'Unknown item')} ✓")
    else:
        lines.append("No shopping list items found.")
    lines.append("")
    
    # Weather & Sun Information
    lines.append("### Weather & Sun")
    weather = state_dict.get("weather.forecast_home", {})
    weather_state = weather.get("state", "N/A")
    weather_attrs = weather.get("attributes", {})
    temp = weather_attrs.get("temperature", "N/A")
    humidity = weather_attrs.get("humidity", "N/A")
    dew = weather_attrs.get("dew_point", "N/A")
    clouds = weather_attrs.get("cloud_coverage", "N/A")
    uv = weather_attrs.get("uv_index", "N/A")
    pressure = weather_attrs.get("pressure", "N/A")
    wind_speed = weather_attrs.get("wind_speed", "N/A")
    wind_bearing = weather_attrs.get("wind_bearing", "N/A")
    
    lines.append(f"- **Forecast:** {weather_state}, {temp}°C, {humidity}% humidity.")
    lines.append(f"  - Dew Point: {dew}°C, Cloud Coverage: {clouds}%, UV Index: {uv}.")
    lines.append(f"  - Pressure: {pressure} hPa, Wind: {wind_speed} m/s from {wind_bearing}°.")
    
    sun = state_dict.get("sun.sun", {})
    sun_attrs = sun.get("attributes", {})
    next_dawn = sun_attrs.get("next_dawn", "N/A")
    next_noon = sun_attrs.get("next_noon", "N/A")
    next_dusk = sun_attrs.get("next_dusk", "N/A")
    next_setting = sun_attrs.get("next_setting", "N/A")
    sun_state = sun.get("state", "N/A")
    
    lines.append(f"- **Sun Status:** Currently {sun_state}.")
    lines.append(f"  - Next Dawn: {next_dawn}")
    lines.append(f"  - Next Noon: {next_noon}")
    lines.append(f"  - Next Dusk: {next_dusk}")
    lines.append(f"  - Next Setting: {next_setting}")
    lines.append("")
    
    # --- Weather Forecast for the Next Couple Days ---
    # This section assumes the weather entity's attributes contain a "forecast" key.
    forecast = weather_attrs.get("forecast", [])
    if forecast:
        lines.append("### Weather Forecast (Next Days)")
        precip_unit = weather_attrs.get("precipitation_unit", "mm")
        for day in forecast:
            # Typical keys include "datetime", "condition", "temperature", "templow", "precipitation"
            dt = day.get("datetime", "N/A")
            condition = day.get("condition", "N/A")
            temp_high = day.get("temperature", "N/A")
            temp_low = day.get("templow", "N/A")
            precipitation = day.get("precipitation", "N/A")
            lines.append(f"- {dt}: {condition}, high: {temp_high}°C, low: {temp_low}°C, precipitation: {precipitation}{precip_unit}")
        lines.append("")
    else:
        lines.append("### Weather Forecast (Next Days)")
        lines.append("- No forecast data available.")
        lines.append("")

    # Updates & Firmware
    lines.append("### Updates & Firmware")
    update_keys = [
        "update.home_assistant_supervisor_update",
        "update.home_assistant_core_update",
        "update.home_assistant_operating_system_update"
    ]
    update_info = []
    for key in update_keys:
        upd = state_dict.get(key, {})
        name = upd.get("attributes", {}).get("friendly_name", key)
        installed = upd.get("attributes", {}).get("installed_version", "N/A")
        update_info.append(f"{name} (v{installed})")
    firmware = state_dict.get("update.vindriktning_firmware", {})
    fw_name = firmware.get("attributes", {}).get("friendly_name", "Firmware")
    fw_installed = firmware.get("attributes", {}).get("installed_version", "N/A")
    fw_latest = firmware.get("attributes", {}).get("latest_version", "N/A")
    
    lines.append("- " + ", ".join(update_info))
    lines.append(f"- {fw_name}: installed v{fw_installed}, latest v{fw_latest}.")
    lines.append("")
    
    # Network & Other Sensors
    lines.append("### Network & Sensors")
    external_ip = state_dict.get("sensor.archera7v5_external_ip", {}).get("state", "N/A")
    
    # Get download and upload speeds, convert to integers if possible
    download_speed_raw = state_dict.get("sensor.archera7v5_download_speed", {}).get("state", "N/A")
    upload_speed_raw = state_dict.get("sensor.archera7v5_upload_speed", {}).get("state", "N/A")
    
    # Convert to integers if the values are numeric
    try:
        download_speed = int(float(download_speed_raw))
    except (ValueError, TypeError):
        download_speed = download_speed_raw
        
    try:
        upload_speed = int(float(upload_speed_raw))
    except (ValueError, TypeError):
        upload_speed = upload_speed_raw
    
    particulate = state_dict.get("sensor.particulate_matter_2_5mm_concentration", {}).get("state", "N/A")
    
    lines.append(f"- **External IP:** {external_ip}")
    lines.append(f"- **Download Speed:** {download_speed} KiB/s, **Upload Speed:** {upload_speed} KiB/s")
    lines.append(f"- **Particulate Matter (2.5µm):** {particulate} µg/m³")
    lines.append("")
    
    return "\n".join(lines)

if __name__ == '__main__':
    async def main():
        dashboard = await get_dashboard_summary()
        print(dashboard)
    
    asyncio.run(main())
