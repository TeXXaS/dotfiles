#!/bin/bash

function set_office() {
	xrandr \
	 --output eDP1 --mode 1920x1080 --pos 0x0 --rotate normal \
	 --output HDMI3 --mode 1920x1080 --pos 1920x0 --rotate normal \
	 --output HDMI2 --mode 1920x1080 --pos 3840x0 --rotate normal \
	 --output DP1 --off \
	 --output DP2 --off \
	 --output HDMI1 --off \
	 --output VGA1 --off \
	 --output VIRTUAL1 --off \

	xfconf-query -c xfce4-panel -p /panels/panel-1/output-name -s monitor-1
	xfconf-query -c xfce4-panel -p /panels/panel-2/output-name -s monitor-1
}

function set_alone() {
	xrandr \
	 --output eDP1 --mode 1920x1080 --pos 0x0 --rotate normal \
	 --output HDMI1 --off \
	 --output DP1 --off \
	 --output DP2 --off \
	 --output HDMI2 --off \
	 --output HDMI3 --off \
	 --output VGA1 --off \
	 --output VIRTUAL1 --off \

	xfconf-query -c xfce4-panel -p /panels/panel-1/output-name -s monitor-0
	xfconf-query -c xfce4-panel -p /panels/panel-2/output-name -s monitor-0
}

if [[ `xrandr --query | grep ' connected' | wc -l` -gt 1 ]]; then 
  set_office
else
  set_alone
fi

