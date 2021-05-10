# Wifi configuration file manypilator for autoap
#
# Copyright (C) 2021 Pontus Borg <glpontus@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.


#
#  Magic strings in wpa_supplicant to look for:
#  STASSID    SSID to use as a STA
#  STAPSK
#  APSSID    SSID to use as an AP
#  APPSK
#

import logging


class Wifi:
    def __init__(self, config):
        self.server = config.get_server()
        self.name = config.get_name()

        self.wpa_supplicant = config.get("wpa_supplicant")

        self.server.register_endpoint("/server/wifi", ['GET'],
                                      self._handle_wifi_request)

    async def _execute_cmd(self, cmd: str) -> None:
        shell_cmd: SCMDComp = self.server.lookup_component('shell_command')
        scmd = shell_cmd.build_shell_command(cmd, None)
        try:
            await scmd.run(timeout=5., verbose=True)
        except Exception:
            logging.exception(f"Error running cmd '{cmd}'")
            raise

    def line_extract_value(self, line):
        # Find the "s
        first = line.find('"')
        last  = len(line) - line[::-1].find('"')
        return line[first+1:last-1]

    async def read_wpa(self, filename):
        old_config: Dict[str, str] = {
            'stassid': "",
            'stapsk' : "",
            'apssid' : "",
            'appsk'  : "",
        }
        
        with open(filename, 'r') as f:
            for line in f:
                if line.find("STASSID") != -1:
                    old_config["stassid"] = self.line_extract_value(line)
                elif line.find("STAPSK") != -1:
                    old_config["stapsk"] = self.line_extract_value(line)
                elif line.find("APSSID") != -1:
                    old_config["apssid"] = self.line_extract_value(line)
                elif line.find("APPSK") != -1:
                    old_config["appsk"] = self.line_extract_value(line)
        return old_config
                


    async def write_wpa(self, filename, config, newfile):

        f2 = open(newfile, 'w')
        with open(filename, 'r') as f:
            for line in f:
                newline = line
                if line.find("STASSID") != -1:
                    newline = "  ssid=\"" + config["stassid"] + "\" # STASSID, Leave this comment in place\n"
                elif line.find("STAPSK") != -1:
                    newline = "  psk=\"" + config["stapsk"] + "\" # STAPSK, Leave this comment in place\n"
                elif line.find("APSSID") != -1:
                    newline = "  ssid=\"" + config["apssid"] + "\" # APSSID, Leave this comment in place\n"
                elif line.find("APPSK") != -1:
                    newline = "  psk=\"" + config["appsk"] + "\" # APPSK, Leave this comment in place\n"
                f2.write(newline)
        f2.close()

    
    async def request_wifi_config(self):
        klippy_apis = self.server.lookup_component('klippy_apis')
        return await klippy_apis.query_objects({'print_stats': None})

    async def _handle_wifi_request(self, web_request):
        config = await self.read_wpa(self.wpa_supplicant)
        
        stassid = web_request.get_str("stassid", None)
        stapsk  = web_request.get_str("stapsk", None)
        apssid  = web_request.get_str("spssid", None)
        appsk   = web_request.get_str("appsk", None)

        if(stassid or stapsk or apssid or appsk):
            if stassid:
                config["stassid"] = stassid
            if stapsk:
                config["stapsk"]  = stapsk
            if apssid:
                config["apssid"]  = apssid
            if appsk:
                config["appsk"]   = appsk
            await self.write_wpa(self.wpa_supplicant, config, "/tmp/wpa.txt")
            await self._execute_cmd(f"sudo /usr/local/sbin/wpacopy /tmp/wpa.txt") 
            #await self._execute_cmd("sudo systemctl restart systemd-networkd") 
            await self._execute_cmd("wpa_cli -i wlan0 reconfigure") 
        return {"wifi": config}

def load_component(config):
    return Wifi(config)        
