#!/opt/thinlinc/libexec/python3
# -*-mode: python; coding: utf-8 -*-
#
# Copyright 2002-2021 Cendio AB.
# For more information, see http://www.cendio.com

import os
import codecs
import traceback
import re
import sys

from urllib.parse import parse_qs

DEFAULT_CLIENTTYPE = "native"
DEFAULT_REDIRTO = ""
REDIR_TIMEOUT = 10000
DEFAULT_AUTOLOGIN = "1"
DEFAULT_START_PROGRAM_ENABLED = "0"
DEFAULT_START_PROGRAM_COMMAND = "firefox"
DEFAULT_SHADOWING_ENABLED = "0"
DEFAULT_SHADOW_NAME = ""

def parse_request(file, encoding = 'utf-8', errors='strict'):

    content_length = -1
    if 'CONTENT_LENGTH' in os.environ:
       content_length = os.environ['CONTENT_LENGTH']
    try:
        content_length = int(content_length)
    except ValueError:
        return None

    content_type = "application/x-www-form-urlencoded"
    if 'CONTENT_TYPE' in os.environ:
       content_type = os.environ['CONTENT_TYPE']

    content_type = content_type.split(';')[0].strip()

    # POST messages must be URL-encoded.
    if content_type != 'application/x-www-form-urlencoded':
        # This should only occurr during development.
        raise ValueError('Handling for Content-Type "%s" not implemented.' %content_type)

    data = file.read(content_length)

    try:
        decoded = data.decode(encoding, errors)
    except UnicodeError:
        return None

    if 'QUERY_STRING' in os.environ:
        decoded += os.environ['QUERY_STRING']

    query = parse_qs(decoded)
    return query

class FormDict(dict):
    def getvalue(self, key, default=None):
        """Mimic behaviour of getvalue()
           from cgi.FieldStorage"""
        val = self.get(key, default)
        if isinstance(val, list):
            return val[0]
        else:
            return val

class Response:
    "A response class. Used during the construction of a response."
    def __init__(self, form):
        self.form = form
        self.env = os.environ
        # We do not use cgi=1, since we are writing the HTTP headers manually

        self.clienttype = self.form.getvalue("clienttype", DEFAULT_CLIENTTYPE)
        # IE is full of bugs wrt caching. See http://support.microsoft.com/kb/234067 and
        # http://www.web-caching.com/msiebugs.html
        self.http_headers = {"Content-type": "text/html; charset=UTF-8",
                             "Expires": "0"}

    def html_begin(self, title="Cendio ThinLinc login"):
        self.doc = """
<!DOCTYPE html>
<HEAD>
  <TITLE>""" + title + """</TITLE>
</HEAD>
<BODY>
        """

    def html_finish(self):
        self.doc += """
</BODY>
</HTML>
        """

    def write_docstart(self):
        http_header = ""
        for key, val in self.http_headers.items():
            http_header += "%s: %s\r\n" % (key, val)
        http_header += "\r\n"
        print(http_header)


    def get_server_name(self):
        server_name = self.env.get("HTTP_HOST")
        if not server_name:
            server_name = self.env.get("SERVER_NAME")
        return server_name


    def _get_https_url_base(self):
        server_name = self.get_server_name()
        script_name = self.env.get("SCRIPT_NAME")
        return "https://" + server_name + script_name


    def get_cgi_bool(self, param, defvalue):
        """Get boolean CGI parameter value. "0", "off", and "false" are false,
        everything else is true"""
        val = self.form.getvalue(param, defvalue)
        if val in ("0", "off", "false"):
            return 0
        else:
            return 1


class Action:
    "Abstract class for actions. Action- and Submit-methods inherits this class."
    def __init__(self, resp):
        self.resp = resp
        # Shortcut
        self.form = resp.form

    def gen_error(self, *msg):
        "Generate error message in bold, with a BR following"
        return '<BR><STRONG>Error: %s </STRONG><BR>' % ' '.join(msg)

    def print_error(self, *msg):
        "Print error message"
        self.resp.doc += self.gen_error(*msg) + """
<BR>
<A HREF="%s">Back to login page</A>
        """ % self.resp._get_https_url_base()

    def get_password(self):
        """Get the password in clear text, using either password or hexpassword parameter"""
        if "hexpassword" in self.form:
            try:
                data = codecs.decode(self.form.getvalue("hexpassword"), "hex")
            except ValueError:
                return ""
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                return ""
        elif "password" in self.form:
            return self.form.getvalue("password")
        else:
            return ""

    def get_hex_password(self):
        """Get the hexified password, using either password or hexpassword parameter"""
        if "hexpassword" in self.form:
            return self.form.getvalue("hexpassword")
        elif "password" in self.form:
            password = self.form.getvalue("password")
            data = codecs.encode(password.encode('utf-8'), "hex")
            return data.decode('ascii')
        else:
            return ""


class LoginPageActions(Action):
    def response(self):
        self.resp.html_begin()
        self.resp.doc += """
<BR><BR>
<H2 STYLE="text-align: center;">Cendio ThinLinc login</H2>
<BR><BR>
        """
        self.resp.doc += self.gen_javascript() + """
<FORM METHOD="POST" ACTION="%s" NAME="loginform" onSubmit="return LoginSubmit();">
  <INPUT TYPE="hidden" NAME="clienttype" VALUE="%s">
  <INPUT TYPE="hidden" NAME="server_name" VALUE="%s">
  <INPUT TYPE="hidden" NAME="autologin" VALUE="%s">
  <INPUT TYPE="hidden" NAME="start_program_enabled" VALUE="%s">
  <INPUT TYPE="hidden" NAME="start_program_command" VALUE="%s">
  <INPUT TYPE="hidden" NAME="shadowing_enabled" VALUE="%s">
  <INPUT TYPE="hidden" NAME="shadow_name" VALUE="%s">
  <TABLE STYLE="margin: auto;">
    <TR>
      <TD STYLE="text-align: right;">Username</TD>
      <TD>
        <INPUT TYPE="TEXT" NAME="username" VALUE="%s" SIZE=20>
      </TD>
    </TR>
    <TR>
      <TD STYLE="text-align: right;">Password</TD>
      <TD>
        <INPUT TYPE="password" NAME="password" VALUE="%s" SIZE=20>
      </TD>
    </TR>
  </TABLE>
  <P STYLE="text-align: center;">
    <INPUT TYPE="submit" NAME="submitbutton" VALUE="Log in">
  </P>
  <INPUT TYPE="hidden" NAME="loginsubmit" VALUE="1">
</FORM>
        """ % (self.resp._get_https_url_base(),
               self.form.getvalue("clienttype", DEFAULT_CLIENTTYPE),
               self.form.getvalue("server_name", self.resp.get_server_name()),
               self.form.getvalue("autologin", DEFAULT_AUTOLOGIN),
               self.form.getvalue("start_program_enabled", DEFAULT_START_PROGRAM_ENABLED),
               self.form.getvalue("start_program_command", DEFAULT_START_PROGRAM_COMMAND),
               self.form.getvalue("shadowing_enabled", DEFAULT_SHADOWING_ENABLED),
               self.form.getvalue("shadow_name", DEFAULT_SHADOW_NAME),
               self.form.getvalue("username", ""),
               self.get_password())

        self.resp.html_finish()


    def gen_javascript(self):
        return """
<script>
<!--
function LoginSubmit() {
    document.loginform.submitbutton.value = "Redirecting in %s seconds...";
    document.loginform.submitbutton.disabled = true;
    setTimeout("Redirect()", %s);
}
function Redirect() {
    location.href = "%s";
}
//-->
</script>
""" % (REDIR_TIMEOUT/1000, REDIR_TIMEOUT, self.form.getvalue("redirto", DEFAULT_REDIRTO))


class RedirectToHTTPS(Action):
    def response(self):
        self.resp.html_begin()
        new_url = self.resp._get_https_url_base()
        self.resp.doc += """
<H2>Unsafe protocol</H2>
Redirecting to
<A HREF="%s">%s</A>
        """ % (new_url, new_url)
        self.resp.http_headers["Refresh"] = "0; URL=%s" % new_url
        self.resp.html_finish()


class DisplayURL(Action):
    def response(self):
        self.resp.html_begin(title="Cendio ThinLinc URL display")
        # Ev. cgi.escape eller URLencode.
        s = ""
        for key in self.form.keys():
            if key in ("testformsubmit", "displayurl"):
                continue
            s += "&%s=%s" % (key, self.form.getvalue(key))
        s = "?" + s[1:]
        self.resp.doc += self.resp._get_https_url_base() + s + '\n'
        self.resp.html_finish()


#
# Used for Native client
#
class LoginPageSubmitNative(Action):
    def response(self):
        server_name = self.form.getvalue("server_name", self.resp.get_server_name())
        username = self.form.getvalue("username", "")
        password_hexascii = self.get_hex_password()
        autologin = self.resp.get_cgi_bool("autologin", DEFAULT_AUTOLOGIN)
        start_program_enabled = self.resp.get_cgi_bool("start_program_enabled",
                                                       DEFAULT_START_PROGRAM_ENABLED)
        start_program_command = self.form.getvalue("start_program_command",
                                                   DEFAULT_START_PROGRAM_COMMAND)
        shadowing_enabled = self.resp.get_cgi_bool("shadowing_enabled",
                                                   DEFAULT_SHADOWING_ENABLED)
        shadow_name = self.form.getvalue("shadow_name", DEFAULT_SHADOW_NAME)
        f = open("/opt/thinlinc/etc/tlclient.conf.webtemplate")
        data = f.read()
        # Do substitutions. Some strings to test with:
        # $password$
        # $password$_and_suffix
        # prefix_and_$password$
        # \$notexpanded
        data = re.sub(r'([^\\])\$server_name\$', r'\g<1>' + server_name, data)
        data = re.sub(r'([^\\])\$login_name\$', r'\g<1>' + username, data)
        data = re.sub(r'([^\\])\$password\$', r'\g<1>' + password_hexascii, data)
        data = re.sub(r'([^\\])\$autologin\$', r'\g<1>' + str(autologin), data)
        data = re.sub(r'([^\\])\$start_program_enabled\$',
                      r'\g<1>' + str(start_program_enabled), data)
        data = re.sub(r'([^\\])\$start_program_command\$',
                      r'\g<1>' + start_program_command, data)
        data = re.sub(r'([^\\])\$shadowing_enabled\$',
                      r'\g<1>' + str(shadowing_enabled), data)
        data = re.sub(r'([^\\])\$shadow_name\$', r'\g<1>' + shadow_name, data)
        data = re.sub(r'\\\$', r'$', data)
        self.resp.doc = data
        f.close()
        # Change the content type last, so that tracebacks are in text/html
        self.resp.http_headers["Content-type"] = \
            "application/vnd.cendio.thinlinc.clientconf; charset=UTF-8"
        self.resp.http_headers["Content-Disposition"] = "inline; filename=launch.tlclient"


def write_traceback(resp):
    resp.html_begin()
    resp.doc += '<H3>Internal server error</H3>'
    resp.doc += '<PRE>' + traceback.format_exc() + '</PRE>'
    resp.html_finish()


if __name__ == "__main__":

    data_dict = parse_request(sys.stdin.buffer)
    resp = Response(FormDict(data_dict))

    try:
        "Do requested actions based on CGI keywords"
        if "HTTPS" not in os.environ:
            # Redirect to HTTPS page
            RedirectToHTTPS(resp).response()
        elif resp.get_cgi_bool("displayurl", "0"):
            DisplayURL(resp).response()
        elif resp.get_cgi_bool("loginsubmit", "0"):
            if resp.clienttype != "native":
                action = Action(resp)
                action.print_error("Unknown client type")
            else:
                LoginPageSubmitNative(resp).response()
        else:
            LoginPageActions(resp).response()
    except:
        write_traceback(resp)

    # Print HTTP header and document
    resp.write_docstart()

    print(resp.doc)
