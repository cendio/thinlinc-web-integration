# Launching the ThinLinc client from a web page

This repo is meant to serve as an example for the Web Integration feature in ThinLinc.

Web Integration allows a web server, such as an intranet or a web portal,
to initiate a ThinLinc client connection with a given configuration on
behalf of a user.

## Requirements

Web Integration requires an Apache HTTP Server, configured for TLS, with
the ability to run CGI scripts.

**Notes**

* Some Linux distributions distributes their Apache HTTP Server with
  the mod_cgi module disabled. This module is required for Web
  Integration to work. On Ubuntu systems, it can be enabled by running
  the :command:`a2enmod cgi` command and restarting the httpd service.
* If Web Integration is used over HTTP, an attacker with access to the
  network may be able to intercept user passwords. To protect from this
  happening, Web Integration automatically redirects to a HTTPS
  connection when HTTP is used.

## Installation

The installation script, `install-web-integration`, is
provided for ease of installation.

```
sudo install-web-integration
```
**Note**

* After installing the Apache HTTP configuration file, make sure to
restart the httpd service to load the new configuration.

While the installation script works as-is on most supported platforms,
two environment variables grants you more control over where the
configuration file is installed. This can be useful if you have httpd
installed at a custom location.

### APACHE_CONF_DIR

If your Apache HTTP Server has been installed to a non-standard
location, set this environment variable to tell the installation
script where the configuration directory is located.

If this parameter is unset, the installation script will attempt to
find the configuration directory from a list of known locations.

   
```
sudo env APACHE_CONF_DIR=/usr/local/etc/httpd/conf.d install-web-integration
```

### APACHE_CONF_NAME

The default behavior of the installation script is to install the
configuration file in the configuration directory with the name
`thinlinc.conf`. If you already have a file with that name in
the configuration directory that you wish to keep, set this
environment variable to a different name.

```
sudo env APACHE_CONF_NAME=web-integration.conf install-web-integration
```

## Usage

The process works like this:

1. The CGI script is called with the desired parameters.

2. The CGI script generates a "launch file", which is a normal client
   configuration file. When the browser receives this file, it launches
   the locally installed ThinLinc client.

The launch file delivered to the client is generated from the template
`/opt/thinlinc/etc/tlclient.conf.webtemplate`. 

**Note**

* The path `/opt/thinlinc/etc/tlclient.conf.webtemplate` is currently hardcoded. Please edit it if you want to use another location.

The CGI script
performs some substitutions on this file, before sending it to the
client. Currently, the following variables are substituted:

``$server_name$``

  * The server name where the CGI script resides.

``$login_name$``

  * The username, specified by the ``username`` CGI parameter.

``$password$``

  * The password in hexadecimal ASCII notation, specified by the
   ``password`` or ``hexpassword`` CGI parameters.

``$autologin$``

  * The value of the ``autologin`` CGI parameter.

## The CGI script tlclient.cgi

The CGI script `tlclient.cgi` is used to start the ThinLinc client,
when launched from a web page. It accepts many parameters which affects
its operation. These are described below:

``server_name``

  * The desired server name.

``username``

  * The desired username. No default.

``password``

  * The desired password, in plain text. No default.

``hexpassword``

  * The desired password, in hexadecimal ASCII notation. This parameter
   overrides the ``password`` parameter. No default.

``redirto``

  * After launching the native client, the browser will redirect to the
   web page specified by this parameter. Default value: the empty
   string.

``loginsubmit``

  * This boolean parameter specifies if a login should be directly
   executed, instead of showing a login form. Default value: ``0``

``autologin``

  * This boolean parameter specifies if the native client should
   automatically connect to the specified server at startup. Default
   value: ``1``

``start_program_enabled``

  * This boolean parameter specifies if the native client should request
   that the server starts the session with the command supplied by the
   client, as indicated by the ``start_program_command`` parameter.
   Default value: ``0``

``start_program_command``

  * This parameter specifies the command to use when starting the
   session. Default value: ``"tl-single-app firefox"``.

``displayurl``

  * This boolean parameter can be used for debugging and development
   purposes. It will display a URL with all submitted parameters, and
   do nothing else. Default value: ``0``

``shadowing_enabled``

  * This boolean parameter specifies if the native client should activate
   shadowing. Default value: ``0``

``shadow_name``

  * This parameter specifies the user to shadow. Default value is the
   empty string.

To make it easier to test various parameters, the HTML file
`cgitest.html` is included. It also demonstrates how to create icons on web
pages, which launches ThinLinc sessions.
