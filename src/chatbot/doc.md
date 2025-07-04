# ModSecurity® Reference Manual {#modsecurity_reference_manual}

## Current as of v2.6 v2.7 v2.8 v2.9 v3.0 {#current_as_of_v2.6_v2.7_v2.8_v2.9_v3.0}

### Copyright © 2004-2022 [Trustwave Holdings, Inc.](https://www.trustwave.com/) {#copyright_2004_2022_trustwave_holdings_inc.}

# Table of Contents {#table_of_contents}

# Introduction

ModSecurity is a web application firewall (WAF). With over 70% of
attacks now carried out over the web application level, organisations
need all the help they can get in making their systems secure. WAFs are
deployed to establish an increased external security layer to detect
and/or prevent attacks before they reach web applications. ModSecurity
provides protection from a range of attacks against web applications and
allows for HTTP traffic monitoring and real-time analysis with little or
no changes to existing infrastructure.

## HTTP Traffic Logging {#http_traffic_logging}

Web servers are typically well-equipped to log traffic in a form useful
for marketing analyses, but fall short logging traffic to web
applications. In particular, most are not capable of logging the request
bodies. Your adversaries know this, and that is why most attacks are now
carried out via POST requests, rendering your systems blind. ModSecurity
makes full HTTP transaction logging possible, allowing complete requests
and responses to be logged. Its logging facilities also allow
fine-grained decisions to be made about exactly what is logged and when,
ensuring only the relevant data is recorded. As some of the request
and/or response may contain sensitive data in certain fields,
ModSecurity can be configured to mask these fields before they are
written to the audit log.

## Real-Time Monitoring and Attack Detection {#real_time_monitoring_and_attack_detection}

In addition to providing logging facilities, ModSecurity can monitor the
HTTP traffic in real time in order to detect attacks. In this case,
ModSecurity operates as a web intrusion detection tool, allowing you to
react to suspicious events that take place at your web systems.

## Attack Prevention and Virtual Patching {#attack_prevention_and_virtual_patching}

ModSecurity can also act immediately to prevent attacks from reaching
your web applications. There are three commonly used approaches:

1.  Negative security model. A negative security model monitors requests
    for anomalies, unusual behaviour, and common web application
    attacks. It keeps anomaly scores for each request, IP addresses,
    application sessions, and user accounts. Requests with high anomaly
    scores are either logged or rejected altogether.
2.  Positive security model. When a positive security model is deployed,
    only requests that are known to be valid are accepted, with
    everything else rejected. This model requires knowledge of the web
    applications you are protecting. Therefore a positive security model
    works best with applications that are heavily used but rarely
    updated so that maintenance of the model is minimized.
3.  Known weaknesses and vulnerabilities. Its rule language makes
    ModSecurity an ideal external patching tool. External patching
    (sometimes referred to as Virtual Patching) is about reducing the
    window of opportunity. Time needed to patch application
    vulnerabilities often runs to weeks in many organisations. With
    ModSecurity, applications can be patched from the outside, without
    touching the application source code (and even without any access to
    it), making your systems secure until a proper patch is applied to
    the application.

## Flexible Rule Engine {#flexible_rule_engine}

A flexible rule engine sits in the heart of ModSecurity. It implements
the ModSecurity Rule Language, which is a specialised programming
language designed to work with HTTP transaction data. The ModSecurity
Rule Language is designed to be easy to use, yet flexible: common
operations are simple while complex operations are possible. Certified
ModSecurity Rules, included with ModSecurity, contain a comprehensive
set of rules that implement general-purpose hardening, protocol
validation and detection of common web application security issues.
Heavily commented, these rules can be used as a learning tool.

## Embedded-mode Deployment {#embedded_mode_deployment}

ModSecurity is an embeddable web application firewall, which means it
can be deployed as part of your existing web server infrastructure
provided your web servers are either Apache, IIS7 or Nginx. This
deployment method has certain advantages:

1.  No changes to existing network. It only takes a few minutes to add
    ModSecurity to your existing web servers. And because it was
    designed to be completely passive by default, you are free to deploy
    it incrementally and only use the features you need. It is equally
    easy to remove or deactivate it if required.
2.  No single point of failure. Unlike with network-based deployments,
    you will not be introducing a new point of failure to your system.
3.  Implicit load balancing and scaling. Because it works embedded in
    web servers, ModSecurity will automatically take advantage of the
    additional load balancing and scalability features. You will not
    need to think of load balancing and scaling unless your existing
    system needs them.
4.  Minimal overhead. Because it works from inside the web server
    process there is no overhead for network communication and minimal
    overhead in parsing and data exchange.
5.  No problem with encrypted or compressed content. Many IDS systems
    have difficulties analysing SSL traffic. This is not a problem for
    ModSecurity because it is positioned to work when the traffic is
    decrypted and decompressed.

## Network-based Deployment {#network_based_deployment}

ModSecurity works equally well when deployed as part of a reverse proxy
server, and many of our customers choose to do so. In this scenario, one
installation of ModSecurity can protect any number of back-end web
servers.

## Portability

ModSecurity is known to work well on a wide range of operating systems.
Our customers are successfully running it on Linux, Windows, Solaris,
FreeBSD, OpenBSD, NetBSD, AIX, Mac OS X, and HP-UX.

## Licensing

ModSecurity is available under the Apache Software License v2
[1](http://www.apache.org/licenses/LICENSE-2.0.txt)

Note : ModSecurity, mod_security, ModSecurity Pro, and ModSecurity Core Rules are trademarks or registered trademarks of Trustwave Holdings, Inc.

# Installation for Apache {#installation_for_apache}

## Prerequisites

### ModSecurity 2.x works only with Apache 2.0.x or higher {#modsecurity_2.x_works_only_with_apache_2.0.x_or_higher}

The ModSecurity team works hard to ensure that ModSecurity version 2.x
will work with all versions of Apache 2.x and higher. If you find
incompatibilities on any version (2.2.x, 2.4.x, or 2.6.x) please
immediately inform the ModSecurity team

### mod_uniqueid

Make sure you have `mod_unique_id` installed. mod_unique_id is packaged
with Apache httpd.

### libapr and libapr-util {#libapr_and_libapr_util}

libapr and libapr-util - <http://apr.apache.org/>

### libpcre

<http://www.pcre.org/>

### libxml2

<http://xmlsoft.org/downloads.html>

### liblua v5.x.x {#liblua_v5.x.x}

This library is optional and only needed if you will be using the new
Lua engine - <http://www.lua.org/download.html>

Note : that ModSecurity requires the dynamic libraries. These are not built by default in the source distribution, so the binary distribution is recommended.

```{=html}
<!-- -->
```

Note : libModSecurity (aka v3) is compatible with Lua 5.2+.

### libcurl v7.15.1 or higher {#libcurl_v7.15.1_or_higher}

If you will be using the ModSecurity Log Collector (mlogc) to send audit
logs to a central repository, then you will also need the curl library.

<http://curl.haxx.se/libcurl/>

Note : Many have had issues with libcurl linked with the GnuTLS library for SSL/TLS support. It is recommended that the openssl library be used for SSL/TLS support in libcurl.

## Installation Methods {#installation_methods}

Before you begin with installation you will need to choose your
preferred installation method. First you need to choose whether to
install the latest version of ModSecurity directly from git (best
features, but possibly unstable) or use the latest stable release
(recommended). If you choose a stable release, it might be possible to
install ModSecurity from binary. It is always possible to compile it
from source code.

The following few pages will give you more information on benefits of
choosing one method over another.

## GitHub Access {#github_access}

If you want to access the latest version of the module you need to get
it from the git repository. The list of changes made since the last
stable release is normally available on the web site (and in the file
CHANGES). The git repository for ModSecurity is hosted by GitHub
(http://www.github.com). You can access it directly or view if through
web using this address: <https://github.com/SpiderLabs/ModSecurity>

To download the lastest TRUNK source code to your computer you need to
execute the following command:

**git**

    $git clone git://github.com/SpiderLabs/ModSecurity.git
    $git checkout remotes/trunk

For v2.6.0 and above, the installation process has changed. Follow these
steps:

1.  cd into the directory - `$cd ModSecurity`
2.  Run autogen.sh script - `$./autogen.sh`
3.  Run configure script - `$./configure`
4.  Run make - `$make`
5.  Run make install - `$make install`
6.  Copy the new mod_security2.so file into the proper Apache modules
    directory -
    `$cp /usr/local/modsecurity/lib/mod_security2.so /usr/local/apache/modules/`

## Stable Release Download {#stable_release_download}

To download the stable release go to
<http://www.modsecurity.org/download/>. Binary distributions are
sometimes available. If they are, they are listed on the download page.
If not download the source code distribution.

## Installation Steps {#installation_steps}

-   Stop Apache httpd
-   Unpack the ModSecurity archive
-   Build

Building differs for UNIX (or UNIX-like) operating systems and Windows.

### UNIX

Run the configure script to generate a Makefile. Typically no options
are needed.

    ./configure

Options are available for more customization (use ./configure \--help
for a full list), but typically you will only need to specify the
location of the apxs command installed by Apache httpd with the
\--with-apxs option.

    ./configure --with-apxs=/path/to/httpd-2.x.y/bin/apxs

Note : There are certain configure options that are meant for debugging an other development use. If enabled, these options can substantially impact performance. These options include all \--debug-\* options as well as the \--enable-performance-measurements options.

Compile with:

    make

Optionally test with:

    make CFLAGS=-DMSC_TEST test

Note : This is step is still a bit experimental. If you have problems, please send the full output and error from the build to the support list. Most common issues are related to not finding the required headers and/or libraries.

Optionally build the ModSecurity Log Collector with:

    make mlogc

Optionally install mlogc: Review the INSTALL file included in the
apache2/mlogc-src directory in the distribution. Install the ModSecurity
module with:

    make install

### Windows (MS VC++ 8) {#windows_ms_vc_8}

Edit Makefile.win to configure the Apache base and library paths.
Compile with: `nmake -f Makefile.win` Install the ModSecurity module
with: `nmake -f Makefile.win install` Copy the libxml2.dll and
lua5.1.dll to the Apache bin directory. Alternatively you can follow the
step below for using LoadFile to load these libraries.

Note : Users should follow the steps present in README_WINDOWS.txt into ModSecurity tarball.

### Edit the main Apache httpd config file (usually httpd.conf) {#edit_the_main_apache_httpd_config_file_usually_httpd.conf}

On UNIX (and Windows if you did not copy the DLLs as stated above) you
must load libxml2 and lua5.1 before ModSecurity with something like
this:

    LoadFile /usr/lib/libxml2.so
    LoadFile /usr/lib/liblua5.1.so

Load the ModSecurity module with:

    LoadModule security2_module modules/mod_security2.so

### Configure ModSecurity {#configure_modsecurity}

### Start Apache httpd {#start_apache_httpd}

You should now have ModSecurity 2.x up and running.

Note : If you have compiled Apache yourself you might experience problems compiling ModSecurity against PCRE. This is because Apache bundles PCRE but this library is also typically provided by the operating system. I would expect most (all) vendor-packaged Apache distributions to be configured to use an external PCRE library (so this should not be a problem).

```{=html}
<!-- -->
```

:   You want to avoid Apache using the bundled PCRE library and
    ModSecurity linking against the one provided by the operating
    system. The easiest way to do this is to compile Apache against the
    PCRE library provided by the operating system (or you can compile it
    against the latest PCRE version you downloaded from the main PCRE
    distribution site). You can do this at configure time using the
    \--with-pcre switch. If you are not in a position to recompile
    Apache, then, to compile ModSecurity successfully, you\'d still need
    to have access to the bundled PCRE headers (they are available only
    in the Apache source code) and change the include path for
    ModSecurity (as you did in step 7 above) to point to them (via the
    \--with-pcre ModSecurity configure option).

```{=html}
<!-- -->
```

:   Do note that if your Apache is using an external PCRE library you
    can compile ModSecurity with WITH_PCRE_STUDY defined,which would
    possibly give you a slight performance edge in regular expression
    processing.

```{=html}
<!-- -->
```

:   Non-gcc compilers may have problems running out-of-the-box as the
    current build system was designed around the gcc compiler and some
    compiler/linker flags may differ. To use a non-gcc compiler you may
    need some manual Makefile tweaks if issues cannot be solved by
    exporting custom CFLAGS and CPPFLAGS environment variables.

```{=html}
<!-- -->
```

:   If you are upgrading from ModSecurity 1.x, please refer to the
    migration matrix at
    <http://www.modsecurity.org/documentation/ModSecurity-Migration-Matrix.pdf>

```{=html}
<!-- -->
```

:   Starting with ModSecurity 2.7.0 there are a few important
    configuration options

1.  **\--enable-pcre-jit** - Enables JIT support from pcre \>= 8.20 that
    can improve regex performance.
2.  **\--enable-lua-cache** - Enables lua vm caching that can improve
    lua script performance. Difference just appears if ModSecurity must
    run more than one script per transaction.
3.  **\--enable-request-early** - On ModSecurity 2.6 phase one has been
    moved to phase 2 hook, if you want to play around it use this
    option.
4.  **\--enable-htaccess-config** - It will allow the follow directives
    to be used into .htaccess files when AllowOverride Options is set :

```{=html}
<!-- -->
```
            - SecAction
            - SecRule

            - SecRuleRemoveByMsg
            - SecRuleRemoveByTag
            - SecRuleRemoveById

            - SecRuleUpdateActionById
            - SecRuleUpdateTargetById
            - SecRuleUpdateTargetByTag
            - SecRuleUpdateTargetByMsg

# NGINX

Use of ModSecurity v2 with NGINX is not supported. Please use
ModSecurity v3 (libModSecurity) instead.

# Installation for Microsoft IIS {#installation_for_microsoft_iis}

Before installing ModSecurity make sure you have Visual Studio 2013
Runtime (vcredist) installed. Vcredist can be downloaded here:
<http://www.visualstudio.com/downloads/download-visual-studio-vs> (note
that, there are two different versions 32 and 64b).

The source code of ModSecurity's IIS components is fully published and
the binary building process is described (see README_WINDOWS.TXT). For
quick installation it is highly recommended to use standard MSI
installer available from SourceForge files repository of ModSecurity
project or use binary package and follow the manual installation steps.

Any installation errors or warning messages are logged in the
application event log under \'ModSecurityIIS Installer\' source.

The OWASP CRS is also installed on the system drive, on the selected
folder. It can be included in any website by adding the following line
to the web.config file, in system.webServer section:

     `<ModSecurity enabled="true" configFile="c:\path\to\owasp_crs\modsecurity_iis.conf" />`{=html}

(relative path can also be used accordingly)

## Manually Installing and Troubleshooting Setup of ModSecurity Module on IIS {#manually_installing_and_troubleshooting_setup_of_modsecurity_module_on_iis}

### Configuration

:   After the installation the module will be running in all websites by
    default. To remove it from a website add to web.config:

```{=html}
<!-- -->
```
    <modules>
        <remove name="ModSecurityIIS" />
    </modules>

:   To configure module in a website add to web.config:

```{=html}
<!-- -->
```
    <?xml version="1.0" encoding="UTF-8"?>
    <configuration>
        <system.webServer>
            <ModSecurity enabled="true" configFile="c:\inetpub\wwwroot\xss.conf" />
        </system.webServer>
    </configuration>

:   where configFile is standard ModSecurity config file.

\
: Events from the module will show up in \"Application\" Windows log.

## Common Problems {#common_problems}

:   If after installation protected website responds with HTTP 503 error
    and event ID 2280 keeps getting logged in the application event log:

```{=html}
<!-- -->
```
    Log Name:      Application
    Source:        Microsoft-Windows-IIS-W3SVC-WP
    Event ID:      2280
    Task Category: None
    Level:         Error
    Keywords:      Classic
    User:          N/A
    Description:
    The Module DLL C:\Windows\system32\inetsrv\modsecurityiis.dll failed to load.  The data is the error.

most likely it means that the installation process has failed and the
ModSecurityIIS.dll module is missing one or more libraries that it
depends on. Repeating installation of the prerequisites and the module
files should fix the problem. The dependency walker tool:

-   <http://www.dependencywalker.com/>

can be used to figure out which library is missing or cannot be loaded.

# Configuration Directives {#configuration_directives}

The following section outlines all of the ModSecurity directives. Most
of the ModSecurity directives can be used inside the various Apache
Scope Directives such as VirtualHost, Location, LocationMatch,
Directory, etc\... There are others, however, that can only be used once
in the main configuration file. This information is specified in the
Scope sections below. The first version to use a given directive is
given in the Version sections below.

These rules, along with the Core rules files, should be contained in
files outside of the httpd.conf file and called up with Apache
\"Include\" directives. This allows for easier updating/migration of the
rules. If you create your own custom rules that you would like to use
with the Core rules, you should create a file called -
modsecurity_crs_15_customrules.conf and place it in the same directory
as the Core rules files. By using this file name, your custom rules will
be called up after the standard ModSecurity Core rules configuration
file but before the other Core rules. This allows your rules to be
evaluated first which can be useful if you need to implement specific
\"allow\" rules or to correct any false positives in the Core rules as
they are applied to your site.

Note : It is highly encouraged that you do not edit the Core rules files themselves but rather place all changes (such as SecRuleRemoveByID, etc\...) in your custom rules file. This will allow for easier upgrading as newer Core rules are released.

## SecAction

**Description:** Unconditionally processes the action list it receives
as the first and only parameter. The syntax of the parameter is
identical to that of the third parameter of `SecRule`.

**Syntax:** `SecAction "action1,action2,action3,...“`

**Scope:** Any

**Version:** 2.0.0

This directive is commonly used to set variables and initialize
persistent collections using the initcol action. For example:

    SecAction nolog,phase:1,initcol:RESOURCE=%{REQUEST_FILENAME}

## SecArgumentSeparator

**Description:** Specifies which character to use as the separator for
application/x-www-form- urlencoded content.

**Syntax:** `SecArgumentSeparator character`

**Default:** &

**Scope:** Main(\< 2.7.0), Any(2.7.0)

**Version:** 2.0.0

This directive is needed if a backend web application is using a
nonstandard argument separator. Applications are sometimes (very rarely)
written to use a semicolon separator. You should not change the default
setting unless you establish that the application you are working with
requires a different separator. If this directive is not set properly
for each web application, then ModSecurity will not be able to parse the
arguments appropriately and the effectiveness of the rule matching will
be significantly decreased.

## SecArgumentsLimit

**Description:** Configures the maximum number of ARGS that will be
accepted for processing.

**Syntax:** `SecArgumentsLimit LIMIT`

**Example Usage:** `SecArgumentsLimit 1000`

**Version:** 2.9.7

**Default:** 1000

Exceeding the limit will set the REQBODY_ERROR variable, and additional
arguments beyond the limit will not be included. With JSON body
processing, there is an additional short-circuit to halt parsing once
the limit is breached. As with the enforcement of other issues that
signal REQBODY_ERROR, a rule should be in place to test this value, like
rule 200002 in modsecurity.conf-recommended.

## SecAuditEngine

**Description:** Configures the audit logging engine.

**Syntax:** `SecAuditEngine RelevantOnly`

**Default:** Off

**Scope:** Any

**Version:** 2.0.0

The SecAuditEngine directive is used to configure the audit engine,
which logs complete transactions. ModSecurity is currently able to log
most, but not all transactions. Transactions involving errors (e.g., 400
and 404 transactions) use a different execution path, which ModSecurity
does not support.

The possible values for the audit log engine are as follows:

-   **On**: log all transactions
-   **Off**: do not log any transactions
-   **RelevantOnly**: only the log transactions that have triggered a
    warning or an error, or have a status code that is considered to be
    relevant (as determined by the SecAuditLogRelevantStatus directive)

Note : If you need to change the audit log engine configuration on a per-transaction basis (e.g., in response to some transaction data), use the ctl action.

The following example demonstrates how SecAuditEngine is used:

    SecAuditEngine RelevantOnly
    SecAuditLog logs/audit/audit.log
    SecAuditLogParts ABCFHZ 
    SecAuditLogType concurrent 
    SecAuditLogStorageDir logs/audit 
    SecAuditLogRelevantStatus ^(?:5|4(?!04))

## SecAuditLog

**Description:** Defines the path to the main audit log file (serial
logging format) or the concurrent logging index file (concurrent logging
format). When used in combination with mlogc (only possible with
concurrent logging), this directive defines the mlogc location and
command line.

**Syntax:** `SecAuditLog /path/to/audit.log`

**Scope:** Any Version: 2.0.0

This file will be used to store the audit log entries if serial audit
logging format is used. If concurrent audit logging format is used this
file will be used as an index, and contain a record of all audit log
files created. If you are planning to use concurrent audit logging to
send your audit log data off to a remote server you will need to deploy
the ModSecurity Log Collector (mlogc), like this:

    SecAuditLog "|/path/to/mlogc /path/to/mlogc.conf"

Note : This audit log file is opened on startup when the server typically still runs as root. You should not allow non-root users to have write privileges for this file or for the directory.

## SecAuditLog2

**Description:** Defines the path to the secondary audit log index file
when concurrent logging is enabled. See SecAuditLog for more details.

**Syntax:** `SecAuditLog2 /path/to/audit.log`

**Scope:** Any

**Version:** 2.1.2

The purpose of SecAuditLog2 is to make logging to two remote servers
possible, which is typically achieved by running two instances of the
mlogc tool, each with a different configuration (in addition, one of the
instances will need to be instructed not to delete the files it
submits). This directive can be used only if SecAuditLog was previously
configured and only if concurrent logging format is used.

## SecAuditLogDirMode

**Description:** Configures the mode (permissions) of any directories
created for the concurrent audit logs, using an octal mode value as
parameter (as used in chmod).

**Syntax:** `SecAuditLogDirMode octal_mode|"default"`

**Default:** 0600

**Scope:** Any

**Version:** 2.5.10

The default mode for new audit log directories (0600) only grants
read/write access to the owner (typically the account under which Apache
is running, for example apache). If access from other accounts is needed
(e.g., for use with mpm-itk), then you may use this directive to grant
additional read and/or write privileges. You should use this directive
with caution to avoid exposing potentially sensitive data to
unauthorized users. Using the value default as parameter reverts the
configuration back to the default setting. This feature is not available
on operating systems not supporting octal file modes.

Example:

    SecAuditLogDirMode 02750

Note : The process umask may still limit the mode if it is being more restrictive than the mode set using this directive.

## SecAuditLogFormat

**Description:** Select the output format of the AuditLogs. The format
can be either the native AuditLogs format or JSON.

**Syntax:** `SecAuditLogFormat JSON|Native`

**Default:** Native

**Scope:** Any

**Version:** 2.9.1

Note : The JSON format is only available if ModSecurity was compiled with support to JSON via the YAJL library. During the compilation time, the yajl-dev package (or similar) must be part of the system. The configure scripts provides information if the YAJL support was enabled or not.

## SecAuditLogFileMode

**Description:** Configures the mode (permissions) of any files created
for concurrent audit logs using an octal mode (as used in chmod). See
SecAuditLogDirMode for controlling the mode of created audit log
directories.

**Syntax:** `SecAuditLogFileMode octal_mode|"default"`

**Default:** 0600

**Scope:** Any

**Version:** 2.5.10

**Example Usage:** `SecAuditLogFileMode 00640`

This feature is not available on operating systems not supporting octal
file modes. The default mode (0600) only grants read/write access to the
account writing the file. If access from another account is needed
(using mpm-itk is a good example), then this directive may be required.
However, use this directive with caution to avoid exposing potentially
sensitive data to unauthorized users. Using the value "default" will
revert back to the default setting.

Note : The process umask may still limit the mode if it is being more restrictive than the mode set using this directive.

## SecAuditLogParts

**Description:** Defines which parts of each transaction are going to be
recorded in the audit log. Each part is assigned a single letter; when a
letter appears in the list then the equivalent part will be recorded.
See below for the list of all parts.

**Syntax:** `SecAuditLogParts PARTLETTERS`

**Example Usage:** `SecAuditLogParts ABCFHZ`

**Scope:** Any Version: 2.0.0

**Default:** ABCFHZ Note

The format of the audit log format is documented in detail in the Audit
Log Data Format Documentation.

Available audit log parts:

-   A: Audit log header (mandatory).
-   B: Request headers.
-   C: Request body (present only if the request body exists and
    ModSecurity is configured to intercept it. This would require
    SecRequestBodyAccess to be set to on).
-   D: Reserved for intermediary response headers; not implemented yet.
-   E: Intermediary response body (present only if ModSecurity is
    configured to intercept response bodies, and if the audit log engine
    is configured to record it. Intercepting response bodies requires
    SecResponseBodyAccess to be enabled). Intermediary response body is
    the same as the actual response body unless ModSecurity intercepts
    the intermediary response body, in which case the actual response
    body will contain the error message (either the Apache default error
    message, or the ErrorDocument page).
-   F: Final response headers (excluding the Date and Server headers,
    which are always added by Apache in the late stage of content
    delivery).
-   G: Reserved for the actual response body; not implemented yet.
-   H: Audit log trailer.
-   I: This part is a replacement for part C. It will log the same data
    as C in all cases except when multipart/form-data encoding in used.
    In this case, it will log a fake application/x-www-form-urlencoded
    body that contains the information about parameters but not about
    the files. This is handy if you don't want to have (often large)
    files stored in your audit logs.
-   J: This part contains information about the files uploaded using
    multipart/form-data encoding.
-   K: This part contains a full list of every rule that matched (one
    per line) in the order they were matched. The rules are fully
    qualified and will thus show inherited actions and default
    operators. Supported as of v2.5.0.
-   Z: Final boundary, signifies the end of the entry (mandatory).

## SecAuditLogRelevantStatus

**Description:** Configures which response status code is to be
considered relevant for the purpose of audit logging.

**Syntax:** `SecAuditLogRelevantStatus REGEX`

**Example Usage:** `SecAuditLogRelevantStatus "^(?:5|4(?!04))"`

**Scope:** Any

**Version:** 2.0.0

**Dependencies/Notes:** Must have SecAuditEngine set to RelevantOnly.
Additionally, the auditlog action is present by default in rules, this
will make the engine bypass the \'SecAuditLogRelevantStatus\' and send
rule matches to the audit log regardless of status. You must specify
noauditlog in the rules manually or set it in SecDefaultAction.

The main purpose of this directive is to allow you to configure audit
logging for only the transactions that have the status code that matches
the supplied regular expression. The example provided would log all 5xx
and 4xx level status codes, except for 404s. Although you could achieve
the same effect with a rule in phase 5, SecAuditLogRelevantStatus is
sometimes better, because it continues to work even when SecRuleEngine
is disabled.

## SecAuditLogStorageDir

**Description:** Configures the directory where concurrent audit log
entries are to be stored.

**Syntax**: `SecAuditLogStorageDir /path/to/storage/dir`

**Example Usage:** `SecAuditLogStorageDir /usr/local/apache/logs/audit`

**Scope:** Any

**Version:** 2.0.0

This directive is only needed when concurrent audit logging is used. The
directory must already exist and must be writable by the web server
user. Audit log entries are created at runtime, after Apache switches to
a non-root account. As with all logging mechanisms, ensure that you
specify a file system location that has adequate disk space and is not
on the main system partition.

## SecAuditLogType

**Description:** Configures the type of audit logging mechanism to be
used.

**Syntax:** `SecAuditLogType Serial|Concurrent|HTTPS`

**Example Usage:** `SecAuditLogType Serial`

**Scope:** Any

**Version:** 2.0.0

The possible values are:

Serial : Audit log entries will be stored in a single file, specified by SecAuditLog. This is conve- nient for casual use, but it can slow down the server, because only one audit log entry can be written to the file at any one time.\
Concurrent : One file per transaction is used for audit logging. This approach is more scalable when heavy logging is required (multiple transactions can be recorded in parallel). It is also the only choice if you need to use remote logging.

```{=html}
<!-- -->
```

HTTPS : This functionality is only available on libModSecurity and its currently in testing phase. Depending on the amount of request that you have, it may be suitable. Use the URL of your endpoint instead of the path to a file.

```{=html}
<!-- -->
```

Note : HTTPS audit log type is currently only supported on libModSecurity.

## SecCacheTransformations

**Description:** Controls the caching of transformations, which may
speed up the processing of complex rule sets. Caching is off by default
starting with 2.5.6, when it was deprecated and downgraded back to
experimental.

**Syntax:** `SecCacheTransformations On|Off [options]`

**Example Usage:** `SecCacheTransformations On "minlen:64,maxlen:0"`

**Scope:** Any

**Version:** 2.5.0; deprecated in 2.5.6.

**Supported on libModSecurity:** No (Deprecated)

The first directive parameter can be one of the following:

-   **On**: Cache transformations (per transaction, per phase) allowing
    identical transforma- tions to be performed only once.
-   **Off**: Do not cache any transformations, leaving all
    transformations to be performed every time they are needed.

The following options are allowed (multiple options must be
comma-separated):

-   **incremental:on\|off**: Enabling this option will cache every
    transformation instead of just the final transformation. The default
    is off.
-   **maxitems:N**: Do not allow more than N transformations to be
    cached. Cache will be disabled once this number is reached. A zero
    value is interpreted as unlimited. This option may be useful to
    limit caching for a form with a large number of variables. The
    default value is 512.
-   **minlen:N**: Do not cache the transformation if the variable's
    length is less than N bytes. The default setting is 32.
-   **maxlen:N**: Do not cache the transformation if the variable's
    length is more than N bytes. A zero value is interpreted as
    unlimited. The default setting is 1024.

## SecChrootDir

**Description:** Configures the directory path that will be used to jail
the web server process.

**Syntax:** `SecChrootDir /path/to/chroot/dir`

**Example Usage:** `SecChrootDir /chroot`

**Scope:** Main

**Version:** 2.0.0-2.9.x

**Supported on libModSecurity:** TBI

This feature is not available on Windows builds. The internal chroot
functionality provided by ModSecurity works great for simple setups. One
example of a simple setup is Apache serving only static files, or
running applications using built-in modules. Some problems you might
encounter with more complex setups:

1.  DNS lookups do not work (this is because this feature requires a
    shared library that is loaded on demand, after chroot takes place).
2.  You cannot send email from PHP, because it wants to use sendmail and
    sendmail re- sides outside the jail.
3.  In some cases, when you separate Apache from its configuration,
    restarts and graceful reloads no longer work.

The best way to use SecChrootDir is the following:

1.  Create /chroot to be your main jail directory.
2.  Create /chroot/opt/apache inside jail.
3.  Create a symlink from /opt/apache to /chroot/opt/apache.
4.  Now install Apache into /chroot/opt/apache.

You should be aware that the internal chroot feature might not be 100%
reliable. Due to the large number of default and third-party modules
available for the Apache web server, it is not possible to verify the
internal chroot works reliably with all of them. A module, working from
within Apache, can do things that make it easy to break out of the jail.
In particular, if you are using any of the modules that fork in the
module initialisation phase (e.g., mod_fastcgi, mod_fcgid, mod_cgid),
you are advised to examine each Apache process and observe its current
working directory, process root, and the list of open files. Consider
what your options are and make your own decision.

Note : This directive is not allowed inside VirtualHosts. If enabled, it must be placed in a global server-wide configuration file such as your default modsecurity.conf.

## SecCollectionTimeout

**Description:** Specifies the collections timeout. Default is 3600
seconds.

**Syntax:** `SecCollectionTimeout seconds`

**Default:** 3600

**Scope:** Any

**Version:** 2.6.3-2.9.x

**Supported on libModSecurity:** No

## SecComponentSignature

**Description:** Appends component signature to the ModSecurity
signature.

**Syntax:** `SecComponentSignature "COMPONENT_NAME/X.Y.Z (COMMENT)"`

**Example usage**: `SecComponentSignature "core ruleset/2.1.3"`

**Scope:** Main

**Version:** 2.5.0-3.x

**Supported on libModSecurity:** Yes

This directive should be used to make the presence of significant rule
sets known. The entire signature will be recorded in the transaction
audit log.

## SecConnEngine

**Description:** Configures the connections engine. This directive
affect the directives: SecConnReadStateLimit and SecConnWriteStateLimit.

**Syntax:** `SecConnEngine On|Off|DetectionOnly`

**Example Usage:** `SecConnEngine On`

**Scope:** Any

**Version:** 2.8.0-2.9.x

**Supported on libModSecurity:** TBI

Possible values are (Same as SecRuleEngine):

-   **On**: process SecConn\[Read\|Write\]StateLimit.
-   **Off**: Ignore the directives SecConn\[Read\|Write\]StateLimit
-   **DetectionOnly**: process SecConn\[Read\|Write\]StateLimit
    definitions in verbose mode but never executes any disruptive
    actions

## SecContentInjection

**Description:** Enables content injection using actions append and
prepend.

**Syntax:** `SecContentInjection On|Off`

**Example Usage:** `SecContentInjection On`

**Scope:** Any

**Version:** 2.5.0-2.9.x

**Supported on libModSecurity:** TBI

This directive provides an easy way to control content injection, no
matter what the rules want to do. It is not necessary to have response
body buffering enabled in order to use content injection.

Note : This directive must ben enabled if you want to use \@rsub + the STREAM\_ variables to manipulate live transactional data.

## SecCookieFormat

**Description:** Selects the cookie format that will be used in the
current configuration context.

**Syntax:** `SecCookieFormat 0|1`

**Example Usage:** `SecCookieFormat 0`

**Scope:** Any

**Version:** 2.0.0-2.9.x

**Supported on libModSecurity:** TBD

The possible values are:

-   **0**: Use version 0 (Netscape) cookies. This is what most
    applications use. It is the default value.
-   **1**: Use version 1 cookies.

Note : Only version 0 (Netscape) cookies is currently supported on libModSecurity (v3)

## SecCookieV0Separator

**Description:** Specifies which character to use as the separator for
cookie v0 content.

**Syntax:** `SecCookieV0Separator character`

**Scope:** Any

**Version:** 2.7.0-2.9.x

**Supported on libModSecurity:** TBI

## SecDataDir

**Description:** Path where persistent data (e.g., IP address data,
session data, and so on) is to be stored.

**Syntax:** `SecDataDir /path/to/dir`

**Example Usage:** `SecDataDir /usr/local/apache/logs/data`

**Scope:** Main

**Version:** 2.0.0-2.9.x

**Supported on libModSecurity:** No

This directive must be provided before initcol, setsid, and setuid can
be used. The directory to which the directive points must be writable by
the web server user.

Note : This directive is not allowed inside VirtualHosts. If enabled, it must be placed in a global server-wide configuration file such as your default modsecurity.conf.

## SecDebugLog

**Description**: Path to the ModSecurity debug log file.

**Syntax:** `SecDebugLog /path/to/modsec-debug.log`

**Example Usage:** `SecDebugLog /usr/local/apache/logs/modsec-debug.log`

**Scope:** Any

**Version:** 2.0.0

**Supported on libModSecurity:** Yes

## SecDebugLogLevel

**Description:** Configures the verboseness of the debug log data.

**Syntax**: `SecDebugLogLevel 0|1|2|3|4|5|6|7|8|9`

**Example Usage:** `SecDebugLogLevel 4`

**Scope:** Any

**Version:** 2.0.0

**Supported on libModSecurity:** Yes

Messages at levels 1--3 are always copied to the Apache error log.
Therefore you can always use level 0 as the default logging level in
production if you are very concerned with performance. Having said that,
the best value to use is 3. Higher logging levels are not recommended in
production, because the heavy logging affects performance adversely.

The possible values for the debug log level are:

-   0: no logging
-   1: errors (intercepted requests) only
-   2: warnings
-   3: notices
-   4: details of how transactions are handled
-   5: as above, but including information about each piece of
    information handled
-   9: log everything, including very detailed debugging information

## SecDefaultAction

**Description**: Defines the default list of actions for a particular
phase, which will be inherited by the rules in the same phase and in the
same configuration context.

**Syntax:** `SecDefaultAction "action1,action2,action3“`

**Example Usage:**
`SecDefaultAction "phase:2,log,auditlog,deny,status:403,tag:'SLA 24/7'“`

**Scope:** Any

**Version:** 2.0.0

**Supported on libModSecurity:** Yes

**Default:** phase:2,log,auditlog,pass

Every rule following a previous `SecDefaultAction` directive in the same
configuration context will inherit its settings unless more specific
actions are used. Every `SecDefaultAction` directive must specify a
disruptive action and a processing phase and cannot contain metadata
actions.

Warning : `SecDefaultAction` is not inherited across configuration contexts. (For an example of why this may be a problem, read the following ModSecurity Blog entry <https://www.trustwave.com/en-us/resources/blogs/spiderlabs-blog/three-modsecurity-rule-language-annoyances/> .)

## SecDisableBackendCompression

**Description:** Disables backend compression while leaving the frontend
compression enabled.

**Syntax:** `SecDisableBackendCompression On|Off`

**Scope:** Any

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBI

**Default:** Off

This directive is necessary in reverse proxy mode when the backend
servers support response compression, but you wish to inspect response
bodies. Unless you disable backend compression, ModSecurity will only
see compressed content, which is not very useful. This directive is not
necessary in embedded mode, because ModSecurity performs inspection
before response compression takes place.

## SecHashEngine

**Description:** Configures the hash engine.

**Syntax:** `SecHashEngine On|Off`

**Example Usage:** `SecHashEngine On`

**Scope**: Any

**Version:** 2.7.1-2.9.x

**Supported on libModSecurity:** TBI

**Default:** Off

The possible values are:

-   **On**: Hash engine can process the request/response data.
-   **Off**: Hash engine will not process any data.

Note : Users must enable stream output variables and content injection.

## SecHashKey

**Description:** Define the key that will be used by HMAC.

**Syntax:** `SecHashKey rand|TEXT KeyOnly|SessionID|RemoteIP`

**Example Usage:** `SecHashKey "this_is_my_key" KeyOnly`

**Scope**: Any

**Version:** 2.7.1-2.9.x

**Supported on libModSecurity:** TBI

ModSecurity hash engine will append, if specified, the user\'s session
id or remote ip to the key before the MAC operation. If the first
parameter is \"rand\" then a random key will be generated and used by
the engine.

## SecHashParam

**Description:** Define the parameter name that will receive the MAC
hash.

**Syntax:** `SecHashParam TEXT`

**Example Usage:** `SecHashParam "hmac"`

**Scope**: Any

**Version:** 2.7.1-2.9.x

**Supported on libModSecurity:** TBI

ModSecurity hash engine will add a new parameter to protected HTML
elements containing the MAC hash.

## SecHashMethodRx

**Description:** Configures what kind of HTML data the hash engine
should sign based on regular expression.

**Syntax:** `SecHashMethodRx TYPE REGEX`

**Example Usage**:
`SecHashMethodRx HashHref "product_info|list_product"`

**Scope:** Any

**Version:** 2.7.1-2.9.x

**Supported on libModSecurity:** TBI

As a initial support is possible to protect HREF, FRAME, IFRAME and FORM
ACTION html elements as well response Location header when http redirect
code are sent.

The possible values for TYPE are:

-   **HashHref**: Used to sign href= html elements
-   **HashFormAction**: Used to sign form action= html elements
-   **HashIframeSrc**: Used to sign iframe src= html elements
-   **HashframeSrc**: Used to sign frame src= html elements
-   **HashLocation**: Used to sign Location response header

Note : This directive is used to sign the elements however user must use the \@validateHash operator to enforce data integrity.

## SecHashMethodPm

**Description:** Configures what kind of HTML data the hash engine
should sign based on string search algoritm.

**Syntax:** `SecHashMethodPm TYPE "string1 string2 string3..."`

**Example Usage**:
`SecHashMethodPm HashHref "product_info list_product"`

**Scope:** Any

**Version:** 2.7.1-2.9.x

**Supported on libModSecurity:** TBI

As a initial support is possible to protect HREF, FRAME, IFRAME and FORM
ACTION html elements as well response Location header when http redirect
code are sent.

The possible values for TYPE are:

-   **HashHref**: Used to sign href= html elements
-   **HashFormAction**: Used to sign form action= html elements
-   **HashIframeSrc**: Used to sign iframe src= html elements
-   **HashframeSrc**: Used to sign frame src= html elements
-   **HashLocation**: Used to sign Location response header

Note : This directive is used to sign the elements however user must use the \@validateHash operator to enforce data integrity.

## SecGeoLookupDb

**Description**: Defines the path to the database that will be used for
geolocation lookups.

**Syntax:** `SecGeoLookupDb /path/to/db`

**Example Usage**: `SecGeoLookupDb /path/to/GeoLiteCity.dat`

**Scope:** Any

**Version:** 2.5.0

**Supported on libModSecurity:** Yes

ModSecurity relies on the free geolocation databases (GeoLite City and
GeoLite Country) that can be obtained from MaxMind
[2](http://www.maxmind.com). Currently ModSecurity only supports the
legacy GeoIP format. Maxmind\'s newer GeoIP2 format is not yet currently
supported.

## SecGsbLookupDb

**Description**: Defines the path to the database that will be used for
Google Safe Browsing (GSB) lookups.

**Syntax:** `SecGsbLookupDb /path/to/db`

**Example Usage**: `SecGsbLookupDb /path/to/GsbMalware.dat`

**Scope:** Any

**Version:** 2.6.0

**Supported on libModSecurity:** TBD

ModSecurity relies on the free Google Safe Browsing database that can be
obtained from the Google GSB API
[3](http://code.google.com/apis/safebrowsing/).

Note : Deprecated in 2.7.0 after Google dev team decided to not allow the database download anymore. After registering and obtaining a Safe Browsing API key, you can automatically download the GSB using a tool like wget. For further information on how to proceed with the download, please visit Google\'s website: <https://developers.google.com/safe-browsing/v3/update-guide>

## SecGuardianLog

**Description:** Configures an external program that will receive the
information about every transaction via piped logging.

**Syntax:** `SecGuardianLog |/path/to/httpd-guardian`

**Example Usage:**
`SecGuardianLog |/usr/local/apache/bin/httpd-guardian`

**Scope:** Main

**Version:** 2.0.0-2.9.x

**Supported on libModSecurity:** TBI

Guardian logging is designed to send the information about every request
to an external program. Because Apache is typically deployed in a
multiprocess fashion, which makes information sharing between processes
difficult, the idea is to deploy a single external process to observe
all requests in a stateful manner, providing additional protection.

Currently the only tool known to work with guardian logging is
httpd-guardian, which is part of the Apache httpd tools project
[4](http://apache-tools.cvs.sourceforge.net/viewvc/apache-tools/apache-tools/).
The httpd-guardian tool is designed to defend against denial of service
attacks. It uses the blacklist tool (from the same project) to interact
with an iptables-based (on a Linux system) or pf-based (on a BSD system)
firewall, dynamically blacklisting the offending IP addresses. It can
also interact with SnortSam [5](http://www.snortsam.net). Assuming
httpd-guardian is already configured (look into the source code for the
detailed instructions), you only need to add one line to your Apache
configuration to deploy it:

    SecGuardianLog |/path/to/httpd-guardian

Note : This directive is not allowed inside VirtualHosts. If enabled, it must be placed in a global server-wide configuration file such as your default modsecurity.conf.

## SecHttpBlKey

**Description:** Configures the user\'s registered Honeypot Project HTTP
BL API Key to use with \@rbl.

**Syntax:** `SecHttpBlKey [12 char access key]`

**Example Usage:** `SecHttpBlKey whdkfieyhtnf`

**Scope:** Main

**Version:** 2.7.0

**Supported on libModSecurity:** Yes

If the \@rbl operator uses the dnsbl.httpbl.org RBL
(http://www.projecthoneypot.org/httpbl_api.php) you must provide an API
key. This key is registered to individual users and is included within
the RBL DNS requests.

## SecInterceptOnError

**Description:** Configures how to respond when rule processing fails.

**Syntax:** `SecInterceptOnError On|Off`

**Example Usage:** `SecInterceptOnError On`

**Scope:** Main

**Version:** 2.6-2.9.x

**Supported on libModSecurity:** TBI

When an operator execution fails, that is it returns greater than 0,
this directive configures how to react. When set to \"Off\", the rule is
just ignored and the engine will continue executing the rules in phase.
When set to \"On\", the rule will be just dropped and no more rules will
be executed in the same phase, also no interception is made.

## SecMarker

**Description:** Adds a fixed rule marker that can be used as a target
in a skipAfter action. A SecMarker directive essentially creates a rule
that does nothing and whose only purpose is to carry the given ID.

**Syntax:** `SecMarker ID|TEXT`

**Example Usage**: `SecMarker 9999`

**Scope:** Any

**Version:** 2.5.0-3.x

**Supported on libModSecurity:** Yes

The value can be either a number or a text string. The SecMarker
directive is available to allow you to choose the best way to implement
a skip-over. Here is an example used from the Core Rule Set:

    SecMarker BEGIN_HOST_CHECK

            SecRule &REQUEST_HEADERS:Host "@eq 0" \
                    "skipAfter:END_HOST_CHECK,phase:2,rev:'2.1.1',t:none,block,msg:'Request Missing a Host Header',id:'960008',tag:'PROTOCOL_VIOLATION/MISSING_HEADER_HOST',tag:'WASCTC/WASC-21',tag:'OWASP_TOP_10/A7',tag:'PCI/6.5.10',severity:'5',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.notice_anomaly_score},setvar:tx.protocol_violation_score=+%{tx.notice_anomaly_score},setvar:tx.%{rule.id}-PROTOCOL_VIOLATION/MISSING_HEADER-%{matched_var_name}=%{matched_var}"
            SecRule REQUEST_HEADERS:Host "^$" \
                    "phase:2,rev:'2.1.1',t:none,block,msg:'Request Missing a Host Header',id:'960008',tag:'PROTOCOL_VIOLATION/MISSING_HEADER_HOST',tag:'WASCTC/WASC-21',tag:'OWASP_TOP_10/A7',tag:'PCI/6.5.10',severity:'5',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.notice_anomaly_score},setvar:tx.protocol_violation_score=+%{tx.notice_anomaly_score},setvar:tx.%{rule.id}-PROTOCOL_VIOLATION/MISSING_HEADER-%{matched_var_name}=%{matched_var}"

    SecMarker END_HOST_CHECK

## SecPcreMatchLimit

**Description**: Sets the match limit in the PCRE library.

**Syntax:** `SecPcreMatchLimit value`

**Example Usage**: `SecPcreMatchLimit 1500`

**Scope:** Main

**Version**: 2.5.12-2.9.x

**Supported on libModSecurity:** TBI

**Default:** 1500

The default can be changed when ModSecurity is prepared for compilation:
the \--enable-pcre-match-limit=val configure option will set a custom
default and the \--disable-pcre-match-limit option will revert back to
the default of the PCRE library. For more information, refer to the
pcre_extra field in the pcreapi man page.

Note : This directive is not allowed inside VirtualHosts. If enabled, it must be placed in a global server-wide configuration file such as your default modsecurity.conf.

## SecPcreMatchLimitRecursion

**Description:** Sets the match limit recursion in the PCRE library.

**Syntax:** `SecPcreMatchLimitRecursion value`

**Example Usage:** `SecPcreMatchLimitRecursion 1500`

**Scope:** Main

**Version:** 2.5.12-2.9.x

**Supported on libModSecurity:** TBI

**Default:** 1500

The default can be changed when ModSecurity is prepared for compilation:
the \--enable-pcre-match-limit-recursion=val configure option will set a
custom default and the \--disable-pcre-match-limit-recursion option will
revert back to the default of the PCRE library. For more information,
refer to the pcre_extra field in the pcreapi man page.

Note : This directive is not allowed inside VirtualHosts. If enabled, it must be placed in a global server-wide configuration file such as your default modsecurity.conf.

## SecReadStateLimit

**Description:** Establishes a per-IP address limit of how many
connections are allowed to be in SERVER_BUSY_READ state.

**Syntax:** `SecReadStateLimit LIMIT`

**Example Usage**: `SecReadStateLimit 50`

**Scope**: Main

**Version**: 2.5.13, DEPRECATED as of v2.8.0.

**Supported on libModSecurity:** No (Deprecated)

**Default:** 0 (no limit)

For v2.8.0 or newest refer to SecConnReadStateLimit.

## SecConnReadStateLimit

**Description:** Establishes a per-IP address limit of how many
connections are allowed to be in SERVER_BUSY_READ state.

**Syntax:** `SecConnReadStateLimit LIMIT OPTIONAL_IP_MATCH_OPERATOR`

**Example Usage**: `SecConnReadStateLimit 50 "!@ipMatch 127.0.0.1"`

**Scope**: Main

**Version**: v2.8.0-2.9.x (Apache only)

**Supported on libModSecurity:** TBI

**Default:** 0 (no limit)

This measure is effective against Slowloris-style attacks from a single
IP address, but it may not be as good against modified attacks that work
by slowly sending request body content. This is because Apache to
switches state to SERVER_BUSY_WRITE once request headers have been read.
As an alternative, consider mod_reqtimeout (part of Apache as of
2.2.15), which is expected be effective against both attack types. See
Blog post on mitigating slow DoS attacks -
<http://blog.spiderlabs.com/2010/11/advanced-topic-of-the-week-mitigating-slow-http-dos-attacks.html>.
v2.8.0 and newest supports the \@ipMatch, \@ipMatchF and
\@ipMatchFromFile operator along with the its negative (e.g. !@ipMatch)
these were used to create suspicious or whitelist. When a suspicious
list is informed, just the IPs that belongs to the list will be
filtered. A combination of suspicious and whitelist is possible by using
multiple definitions of SecConnReadStateLimit, note, however, that the
limit will be always overwrite by its successor.

**Note:** This functionality is Apache only.

**Note 2:** Make sure
[Reference-Manual#secconnengine](Reference-Manual#secconnengine "wikilink")
is on prior to use this feature.

## SecSensorId

**Description:** Define a sensor ID that will be present into log part
H.

**Syntax:** `SecSensorId TEXT`

**Example Usage**: `SecSensorId WAFSensor01`

**Scope**: Main

**Version**: 2.7.0-2.9.x

**Supported on libModSecurity:** TBI

## SecWriteStateLimit

**Description:** Establishes a per-IP address limit of how many
connections are allowed to be in SERVER_BUSY_WRITE state.

**Syntax:** `SecWriteStateLimit LIMIT`

**Example Usage**: `SecWriteStateLimit 50`

**Scope**: Main

**Version**: 2.6.0, DEPRECATED as of v2.8.0.

**Supported on libModSecurity:** No (Deprecated)

**Default:** 0 (no limit)

For v2.8.0 or newest refer to SecConnWriteStateLimit.

## SecConnWriteStateLimit

**Description:** Establishes a per-IP address limit of how many
connections are allowed to be in SERVER_BUSY_WRITE state.

**Syntax:** `SecConnWriteStateLimit LIMIT OPTIONAL_IP_MATCH_OPERATOR`

**Example Usage**: `SecConnWriteStateLimit 50 "!@ipMatch 127.0.0.1"`

**Scope**: Main

**Version**: 2.6.0-2.9.x (Apache only)

**Supported on libModSecurity:** TBI

**Default:** 0 (no limit)

This measure is effective against Slow DoS request body attacks. v2.8.0
and newest supports the \@ipMatch, \@ipMatchF and \@ipMatchFromFile
operator along with the its negative (e.g. !@ipMatch) these were used to
create suspicious or whitelist. When a suspicious list is informed, just
the IPs that belongs to the list will be filtered. A combination of
suspicious and whitelist is possible by using multiple definitions of
SecConnReadStateLimit, note, however, that the limit will be always
overwrite by its successor.

**Note:** This functionality is Apache only.

**Note 2:** Make sure
[Reference-Manual#secconnengine](Reference-Manual#secconnengine "wikilink")
is on prior to use this feature.

## SecRemoteRules

**Description**: Load rules from a given file hosted on a HTTPS site.

**Syntax:** `SecRemoteRules [crypto] key `[`https://url`](https://url)

**Example Usage**:
`SecRemoteRules some-key `[`https://www.yourserver.com/plain-text-rules.txt`](https://www.yourserver.com/plain-text-rules.txt)

**Scope:** Any

**Version:** 2.9.0-RC1+

**Supported on libModSecurity:** Yes

This is an optional directive that allow the user to load rules from a
remote server. Notice that besides the URL the user also needs to supply
a key, which could be used by the target server to provide different
content for different keys.

Along with the key, supplied by the users, ModSecurity will also send
its Unique ID and the \`status call\' in the format of headers to the
target web server. The following headers are used:

`- ModSec-status`\
`- ModSec-unique-id`\
`- ModSec-key`

The optional option \"crypto\" tells ModSecurity to expect some
encrypted content from server. The utilization of SecRemoteRules is only
allowed over TLS, thus, this option may not be necessary.

Note : A valid and trusted digital certificate is expected on the end server. It is also expected that the server uses TLS, preferable TLS 1.2.

## SecRemoteRulesFailAction

**Description**: Action that will be taken if SecRemoteRules specify an
URL that ModSecurity was not able to download.

**Syntax:** `SecRemoteRulesFailAction Abort|Warn`

**Example Usage**: `SecRemoteRulesFailAction Abort`

**Scope:** Any

**Version:** 2.9.0-RC1+

**Supported on libModSecurity:** Yes

The default action is to Abort whenever there is a problem downloading a
given URL.

Note : This directive also influences the behaviour of \@ipMatchFromFile when used with a HTTPS URI to retrieve the remote file.

## SecRequestBodyAccess

**Description**: Configures whether request bodies will be buffered and
processed by ModSecurity.

**Syntax:** `SecRequestBodyAccess On|Off`

**Example Usage**: `SecRequestBodyAccess On`

**Scope:** Any

**Version:** 2.0.0

**Supported on libModSecurity:** Yes

This directive is required if you want to inspect the data transported
request bodies (e.g., POST parameters). Request buffering is also
required in order to make reliable blocking possible. The possible
values are:

-   On: buffer request bodies
-   Off: do not buffer request bodies

## SecRequestBodyInMemoryLimit

**Description**: Configures the maximum request body size that
ModSecurity will store in memory.

**Syntax:** `SecRequestBodyInMemoryLimit LIMIT_IN_BYTES`

**Example Usage:** `SecRequestBodyInMemoryLimit 131072`

**Scope:** Any

**Version:** 2.0.0-2.9.x

**Supported on libModSecurity:** No

**Default:** 131072 (128 KB)

When a multipart/form-data request is being processed, once the
in-memory limit is reached, the request body will start to be streamed
into a temporary file on disk.

Note : libModSecurity is able to deal with request body in a file or in a buffer (chunked or not). Web servers have properties which controls whenever a request should be saved to a file or used as a buffer (e.g. client_body_buffer_size [6](https://nginx.org/en/docs/http/ngx_http_core_module.html#client_body_buffer_size)) . If it is a file, ModSecurity will use the file to perform the inspection. If not, the buffer will be used.

## SecRequestBodyJsonDepthLimit

**Description:** Configures the maximum parsing depth that is allowed
when parsing a JSON object.

**Syntax:** `SecRequestBodyJsonDepthLimit LIMIT`

**Example Usage:** `SecRequestBodyJsonDepthLimit 5000`

**Scope:** Any

**Version:** 2.9.5- , 3.0.6-

**Supported on libModSecurity:** Yes - as of 3.0.6

**Default:** 10000

During parsing of a JSON object, if nesting exceeds the configured depth
limit then parsing will halt and REQBODY_ERROR will be set.

## SecRequestBodyLimit

**Description:** Configures the maximum request body size ModSecurity
will accept for buffering.

**Syntax:** `SecRequestBodyLimit LIMIT_IN_BYTES`

**Example Usage:** `SecRequestBodyLimit 134217728`

**Scope:** Any

**Version:** 2.0.0

**Supported on libModSecurity:** Yes

**Default:** 134217728 (131072 KB)

Anything over the limit will be rejected with status code 413 (Request
Entity Too Large). There is a hard limit of 1 GB.

Note : In ModSecurity 2.5.x and earlier, SecRequestBodyLimit works only when used in the main server configuration, or a VirtualHost container. In these versions, request body limit is enforced immediately after phase 1, but before phase 2 configuration (i.e. whatever is placed in a Location container) is resolved. You can work around this limitation by using a phase 1 rule that changes the request body limit dynamically, using the ctl:requestBodyLimit action. ModSecurity 2.6.x (currently in the trunk only) and better do not have this limitation.

## SecRequestBodyNoFilesLimit

**Description**: Configures the maximum request body size ModSecurity
will accept for buffering, excluding the size of any files being
transported in the request. This directive is useful to reduce
susceptibility to DoS attacks when someone is sending request bodies of
very large sizes. Web applications that require file uploads must
configure SecRequestBodyLimit to a high value, but because large files
are streamed to disk, file uploads will not increase memory consumption.
However, it's still possible for someone to take advantage of a large
request body limit and send non-upload requests with large body sizes.
This directive eliminates that loophole.

**Syntax:** `SecRequestBodyNoFilesLimit NUMBER_IN_BYTES`

**Example Usage:** `SecRequestBodyNoFilesLimit 131072`

**Scope:** Any

**Version**: 2.5.0

**Supported on libModSecurity:** No

**Default:** 1048576 (1 MB)

Generally speaking, the default value is not small enough. For most
applications, you should be able to reduce it down to 128 KB or lower.
Anything over the limit will be rejected with status code 413 (Request
Entity Too Large). There is a hard limit of 1 GB.

## SecRequestBodyLimitAction

**Description**: Controls what happens once a request body limit,
configured with SecRequestBodyLimit, is encountered

**Syntax:** `SecRequestBodyLimitAction Reject|ProcessPartial`

**Example Usage:** `SecRequestBodyLimitAction ProcessPartial`

**Scope:** Any

**Version**: 2.6.0

**Supported on libModSecurity:** Yes

By default, ModSecurity will reject a request body that is longer than
specified. This is problematic especially when ModSecurity is being run
in DetectionOnly mode and the intent is to be totally passive and not
take any disruptive actions against the transaction. With the ability to
choose what happens once a limit is reached, site administrators can
choose to inspect only the first part of the request, the part that can
fit into the desired limit, and let the rest through. This is not ideal
from a possible evasion issue perspective, however it may be acceptable
under certain circumstances.

Note : When the SecRuleEngine is set to DetectionOnly, SecRequestBodyLimitAction is automatically set to ProcessPartial in order to not cause any disruptions. If you want to know if/when a request body size is over your limit, you can create a rule to check for the existence of the INBOUND_DATA_ERROR variable.

## SecResponseBodyLimit

**Description:** Configures the maximum response body size that will be
accepted for buffering.

**Syntax:** `SecResponseBodyLimit LIMIT_IN_BYTES`

**Example Usage:** `SecResponseBodyLimit 524228`

**Scope:** Any

**Version:** 2.0.0

**Supported on libModSecurity:** Yes

**Default**: 524288 (512 KB)

Anything over this limit will be rejected with status code 500 (Internal
Server Error). This setting will not affect the responses with MIME
types that are not selected for buffering. There is a hard limit of 1
GB.

## SecResponseBodyLimitAction

**Description:** Controls what happens once a response body limit,
configured with SecResponseBodyLimit, is encountered.

**Syntax:** `SecResponseBodyLimitAction Reject|ProcessPartial`

**Example Usage:** `SecResponseBodyLimitAction ProcessPartial`

**Scope:** Any

**Version:** 2.5.0

**Supported on libModSecurity:** Yes

By default, ModSecurity will reject a response body that is longer than
specified. Some web sites, however, will produce very long responses,
making it difficult to come up with a reasonable limit. Such sites would
have to raise the limit significantly to function properly, defying the
purpose of having the limit in the first place (to control memory
consumption). With the ability to choose what happens once a limit is
reached, site administrators can choose to inspect only the first part
of the response, the part that can fit into the desired limit, and let
the rest through. Some could argue that allowing parts of responses to
go uninspected is a weakness. This is true in theory, but applies only
to cases in which the attacker controls the output (e.g., can make it
arbitrary long). In such cases, however, it is not possible to prevent
leakage anyway. The attacker could compress, obfuscate, or even encrypt
data before it is sent back, and therefore bypass any monitoring device.

## SecResponseBodyMimeType

**Description:** Configures which MIME types are to be considered for
response body buffering.

**Syntax:** `SecResponseBodyMimeType MIMETYPE MIMETYPE ...`

**Example Usage**:
`SecResponseBodyMimeType text/plain text/html text/xml`

**Scope:** Any

**Version:** 2.0.0

**Supported on libModSecurity:** Yes

**Default:** text/plain text/html

Multiple SecResponseBodyMimeType directives can be used to add MIME
types. Use SecResponseBodyMimeTypesClear to clear previously configured
MIME types and start over.

Note : Users that wish to perform JSON body inspection on response (phase 4) need to add \_application/json\_ to SecResponseBodyMimeType.

## SecResponseBodyMimeTypesClear

**Description:** Clears the list of MIME types considered for response
body buffering, allowing you to start populating the list from scratch.

**Syntax:** `SecResponseBodyMimeTypesClear`

**Example Usage:** `SecResponseBodyMimeTypesClear`

**Scope:** Any

**Version:** 2.0.0-2.9.x

**Supported on libModSecurity:** TBI

## SecResponseBodyAccess

**Description:** Configures whether response bodies are to be buffered.

**Syntax:** `SecResponseBodyAccess On|Off`

**Example Usage:** `SecResponseBodyAccess On`

**Scope:** Any

**Version:** 2.0.0

**Supported on libModSecurity:** Yes

**Default:** Off

This directive is required if you plan to inspect HTML responses and
implement response blocking. Possible values are:

-   On: buffer response bodies (but only if the response MIME type
    matches the list configured with SecResponseBodyMimeType).
-   Off: do not buffer response bodies.

## SecRule

**Description:** Creates a rule that will analyze the selected variables
using the selected operator.

**Syntax:** `SecRule VARIABLES OPERATOR [ACTIONS]`

**Example Usage:** `SecRule ARGS "@rx attack" "phase:1,log,deny,id:1"`

**Scope:** Any

**Version:** 2.0.0

**Supported on libModSecurity:** Yes

Every rule must provide one or more variables along with the operator
that should be used to inspect them. If no actions are provided, the
default list will be used. (There is always a default list, even if one
was not explicitly set with SecDefaultAction.) If there are actions
specified in a rule, they will be merged with the default list to form
the final actions that will be used. (The actions in the rule will
overwrite those in the default list.) Refer to SecDefaultAction for more
information.

## SecRuleInheritance

**Description:** Configures whether the current context will inherit the
rules from the parent context.

**Syntax:** `SecRuleInheritance On|Off`

**Example Usage:** `SecRuleInheritance Off`

**Scope:** Any

**Version:** 2.0.0-2.9.x

**Supported on libModSecurity:** TBI

**Default:** On

Sometimes when you create a more specific configuration context (for
example using the `<Location>`{=html} container), you may wish to use a
different set of rules than those used in the parent context. By setting
SecRuleInheritance to Off, you prevent the parent rules to be inherited,
which allows you to start from scratch. In ModSecurity 2.5.x it is not
possible to override phase 1 rules from a `<Location>`{=html}
configuration context. There are no limitations in that respect in the
current development version (and there won't be in the next major
version).

The possible values are:

-   On: inherit rules from the parent context
-   Off: do not inherit rules from the parent context

Note : Configuration contexts are an Apache concept. Directives `<Directory>`{=html}, `<Files>`{=html}, `<Location>`{=html}, and `<VirtualHost>`{=html} are all used to create configuration contexts. For more information, please go to the Apache documentation, under Configuration Sections [7](http://httpd.apache.org/docs/2.0/sections.html). This directive does not affect how configuration options are inherited.

## SecRuleEngine

**Description:** Configures the rules engine.

**Syntax:** `SecRuleEngine On|Off|DetectionOnly`

**Example Usage:** `SecRuleEngine On`

**Scope**: Any

**Version:** 2.0.0

**Supported on libModSecurity:** Yes

**Default:** Off

The possible values are:

-   **On**: process rules
-   **Off**: do not process rules
-   **DetectionOnly**: process rules but never executes any disruptive
    actions (block, deny, drop, allow, proxy and redirect)

## SecRulePerfTime

**Description:** Set a performance threshold for rules. Rules that spend
at least the time defined will be logged into audit log Part H as
Rules-Performance-Info in the format id=usec, comma separated.

**Syntax:** `SecRulePerfTime USECS`

**Example Usage:** `SecRulePerfTime 1000`

**Scope:** Any

**Version:** 2.7-2.9.x

**Supported on libModSecurity:** TBI

The rules hitting the threshold can be accessed via the collection
PERF_RULES.

## SecRuleRemoveById

**Description:** Removes the matching rules from the current
configuration context.

**Syntax:** `SecRuleRemoveById ID ID RANGE ...`

**Example Usage:** `SecRuleRemoveByID 1 2 "9000-9010"`

**Scope:** Any

**Version:** 2.0.0 - 3.x

**Supported on libModSecurity:** Yes

This directive supports multiple parameters, each of which can be a rule
ID or a range. Parameters that contain spaces must be delimited using
double quotes.

Note : **This directive must be specified after the rule in which it is disabling**. This should be used within local custom rule files that are processed after third party rule sets. Example file - modsecurity_crs_60_customrules.conf.

## SecRuleRemoveByMsg

**Description:** Removes the matching rules from the current
configuration context.

**Syntax:** `SecRuleRemoveByMsg REGEX`

**Example Usage:** `SecRuleRemoveByMsg "FAIL"`

**Scope:** Any

**Version:** 2.0.0-3.x

**Supported on libModSecurity:** Yes

Normally, you would use SecRuleRemoveById to remove rules, but that
requires the rules to have IDs defined. If they don't, then you can
remove them with SecRuleRemoveByMsg, which matches a regular expression
against rule messages.

Note : This directive must be specified after the rule in which it is disabling. This should be used within local custom rule files that are processed after third party rule sets. Example file - modsecurity_crs_60_customrules.conf.

## SecRuleRemoveByTag

**Description:** Removes the matching rules from the current
configuration context.

**Syntax:** `SecRuleRemoveByTag REGEX`

**Example Usage:** `SecRuleRemoveByTag "WEB_ATTACK/XSS"`

**Scope:** Any

**Version:** 2.6-3.x

**Supported on libModSecurity:** Yes

Normally, you would use SecRuleRemoveById to remove rules, but that
requires the rules to have IDs defined. If they don't, then you can
remove them with SecRuleRemoveByTag, which matches a regular expression
against rule tag data. This is useful if you want to disable entire
groups of rules based on tag data. Example tags used in the OWASP
ModSecurity CRS include:

-   AUTOMATION/MALICIOUS
-   AUTOMATION/MISC
-   AUTOMATION/SECURITY_SCANNER
-   LEAKAGE/SOURCE_CODE_ASP_JSP
-   LEAKAGE/SOURCE_CODE_CF
-   LEAKAGE/SOURCE_CODE_PHP
-   WEB_ATTACK/CF_INJECTION
-   WEB_ATTACK/COMMAND_INJECTION
-   WEB_ATTACK/FILE_INJECTION
-   WEB_ATTACK/HTTP_RESPONSE_SPLITTING
-   WEB_ATTACK/LDAP_INJECTION
-   WEB_ATTACK/PHP_INJECTION
-   WEB_ATTACK/REQUEST_SMUGGLING
-   WEB_ATTACK/SESSION_FIXATION
-   WEB_ATTACK/SQL_INJECTION
-   WEB_ATTACK/SSI_INJECTION
-   WEB_ATTACK/XSS

Note : This directive must be specified after the rule in which it is disabling. This should be used within local custom rule files that are processed after third party rule sets. Example file - modsecurity_crs_60_customrules.conf.

## SecRuleScript

Description: This directive creates a special rule that executes a Lua
script to decide whether to match or not. The main difference from
SecRule is that there are no targets nor operators. The script can fetch
any variable from the ModSecurity context and use any (Lua) operator to
test them. The second optional parameter is the list of actions whose
meaning is identical to that of SecRule.

**Syntax:** `SecRuleScript /path/to/script.lua [ACTIONS]`

**Example Usage:** `SecRuleScript "/path/to/file.lua" "block"`

**Scope:** Any

**Version:** 2.5.0-3.x

**Supported on libModSecurity:** Yes

Note : All Lua scripts are compiled at configuration time and cached in memory. To reload scripts you must reload the entire ModSecurity configuration by restarting Apache.

Example script:

    -- Your script must define the main entry
    -- point, as below.
    function main()
        -- Log something at level 1. Normally you shouldn't be
        -- logging anything, especially not at level 1, but this is
        -- just to show you can. Useful for debugging.
        m.log(1, "Hello world!");

        -- Retrieve one variable.
        local var1 = m.getvar("REMOTE_ADDR");

        -- Retrieve one variable, applying one transformation function.
        -- The second parameter is a string.
        local var2 = m.getvar("ARGS", "lowercase");

        -- Retrieve one variable, applying several transformation functions.
        -- The second parameter is now a list. You should note that m.getvar()
        -- requires the use of comma to separate collection names from
        -- variable names. This is because only one variable is returned.
        local var3 = m.getvar("ARGS.p", { "lowercase", "compressWhitespace" } );

        -- If you want this rule to match return a string
        -- containing the error message. The message must contain the name
        -- of the variable where the problem is located.
        -- return "Variable ARGS:p looks suspicious!"

        -- Otherwise, simply return nil.
        return nil;
    end

In this first example we were only retrieving one variable at the time.
In this case the name of the variable is known to you. In many cases,
however, you will want to examine variables whose names you won\'t know
in advance, for example script parameters.

Example showing use of m.getvars() to retrieve many variables at once:

    function main()
        -- Retrieve script parameters.
        local d = m.getvars("ARGS", { "lowercase", "htmlEntityDecode" } );

        -- Loop through the parameters.
        for i = 1, #d do
            -- Examine parameter value.
            if (string.find(d[i].value, "<script")) then
                -- Always specify the name of the variable where the
                -- problem is located in the error message.
                return ("Suspected XSS in variable " .. d[i].name .. ".");
            end
        end

        -- Nothing wrong found.
        return nil;
    end

Note : Go to <http://www.lua.org/> to find more about the Lua programming language. The reference manual too is available online, at <http://www.lua.org/manual/5.1/>.

```{=html}
<!-- -->
```

Note : Lua support is marked as experimental as the way the programming interface may continue to evolve while we are working for the best implementation style. Any user input into the programming interface is appreciated.

```{=html}
<!-- -->
```

Note : libModSecurity (aka v3) is compatible with Lua 5.2+.

## SecRuleUpdateActionById

**Description:** Updates the action list of the specified rule.

**Syntax:** `SecRuleUpdateActionById RULEID[:offset] ACTIONLIST`

**Example Usage:** `SecRuleUpdateActionById 12345 "deny,status:403"`

**Scope:** Any

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBI

This directive will overwrite the action list of the specified rule with
the actions provided in the second parameter. It has two limitations: it
cannot be used to change the ID or phase of a rule. Only the actions
that can appear only once are overwritten. The actions that are allowed
to appear multiple times in a list, will be appended to the end of the
list.

    SecRule ARGS attack "phase:2,id:12345,t:lowercase,log,pass,msg:'Message text'"
    SecRuleUpdateActionById 12345 "t:none,t:compressWhitespace,deny,status:403,msg:'New message text'"

The effective resulting rule in the previous example will be as follows:

    SecRule ARGS attack "phase:2,id:12345,t:lowercase,t:none,t:compressWhitespace,deny,status:403,msg:'New Message text'"

The addition of t:none will neutralize any previous transformation
functions specified (t:lowercase, in the example).

Note : If the target rule is a chained rule, you must currently specify chain in the SecRuleUpdateActionById action list as well. This will be fixed in a future version.

## SecRuleUpdateTargetById

**Description:** Updates the target (variable) list of the specified
rule.

**Syntax:**
`SecRuleUpdateTargetById RULEID TARGET1[,TARGET2,TARGET3] REPLACED_TARGET`

**Example Usage:** `SecRuleUpdateTargetById 12345 "!ARGS:foo"`

**Scope:** Any

**Version:** 2.6-3.x

**Supported on libModSecurity:** Yes

This directive will append (or replace) variables to the current target
list of the specified rule with the targets provided in the second
parameter. Starting with 2.7.0 this feature supports id range.

**Explicitly Appending Targets**

This is useful for implementing exceptions where you want to externally
update a target list to exclude inspection of specific variable(s).

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/* "[\;\|\`]\W*?\bmail\b" \
         "phase:2,rev:'2.1.1',capture,t:none,t:htmlEntityDecode,t:compressWhitespace,t:lowercase,ctl:auditLogParts=+E,block,msg:'System Command Injection',id:'958895',tag:'WEB_ATTACK/COMMAND_INJECTION',tag:'WASCTC/WASC-31',tag:'OWASP_TOP_10/A1',tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.command_injection_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/COMMAND_INJECTION-%{matched_var_name}=%
    {tx.0}"

    SecRuleUpdateTargetById 958895 !ARGS:email

The effective resulting rule in the previous example will append the
target to the end of the variable list as follows:

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/*|!ARGS:email "[\;\|\`]\W*?\bmail\b" \
         "phase:2,rev:'2.1.1',capture,t:none,t:htmlEntityDecode,t:compressWhitespace,t:lowercase,ctl:auditLogParts=+E,block,msg:'System Command Injection',id:'958895',tag:'WEB_ATTACK/COMMAND_INJECTION',tag:'WASCTC/WASC-31',tag:'OWASP_TOP_10/A1',tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.command_injection_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/COMMAND_INJECTION-%{matched_var_name}=%
    {tx.0}""

Note that is is also possible to use regular expressions in the target
specification:

    SecRuleUpdateTargetById 981172 "!REQUEST_COOKIES:/^appl1_.*/"

**Explicitly Replacing Targets**

You can also entirely replace the target list to something more
appropriate for your environment. For example, lets say you want to
inspect REQUEST_URI instead of REQUEST_FILENAME, you could do this:

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/* "[\;\|\`]\W*?\bmail\b" \
         "phase:2,rev:'2.1.1',capture,t:none,t:htmlEntityDecode,t:compressWhitespace,t:lowercase,ctl:auditLogParts=+E,block,msg:'System Command Injection',id:'958895',tag:'WEB_ATTACK/COMMAND_INJECTION',tag:'WASCTC/WASC-31',tag:'OWASP_TOP_10/A1',tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.command_injection_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/COMMAND_INJECTION-%{matched_var_name}=%
    {tx.0}"

    SecRuleUpdateTargetById 958895 REQUEST_URI REQUEST_FILENAME

The effective resulting rule in the previous example replaces the target
in the begin of the variable list as follows:

    SecRule REQUEST_URI|ARGS_NAMES|ARGS|XML:/* "[\;\|\`]\W*?\bmail\b" \
         "phase:2,rev:'2.1.1',capture,t:none,t:htmlEntityDecode,t:compressWhitespace,t:lowercase,ctl:auditLogParts=+E,block,msg:'System Command Injection',id:'958895',tag:'WEB_ATTACK/COMMAND_INJECTION',tag:'WASCTC/WASC-31',tag:'OWASP_TOP_10/A1',tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.command_injection_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/COMMAND_INJECTION-%{matched_var_name}=%
    {tx.0}""

Note : You could also do the same by using the ctl action with the ruleRemoveById directive. That would be useful if you want to only update the targets for a particular URL, thus conditionally appending targets.

## SecRuleUpdateTargetByMsg

**Description:** Updates the target (variable) list of the specified
rule by rule message.

**Syntax:**
`SecRuleUpdateTargetByMsg TEXT TARGET1[,TARGET2,TARGET3] REPLACED_TARGET`

**Example Usage:**
`SecRuleUpdateTargetByMsg "Cross-site Scripting (XSS) Attack" "!ARGS:foo"`

**Scope:** Any

**Version:** 2.7-3.x

**Supported on libModSecurity:** Yes

This directive will append (or replace) variables to the current target
list of the specified rule with the targets provided in the second
parameter.

**Explicitly Appending Targets**

This is useful for implementing exceptions where you want to externally
update a target list to exclude inspection of specific variable(s).

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/* "[\;\|\`]\W*?\bmail\b" \
         "phase:2,rev:'2.1.1',capture,t:none,t:htmlEntityDecode,t:compressWhitespace,t:lowercase,ctl:auditLogParts=+E,block,msg:'System Command Injection',id:'958895',tag:'WEB_ATTACK/COMMAND_INJECTION',tag:'WASCTC/WASC-31',tag:'OWASP_TOP_10/A1',tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.command_injection_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/COMMAND_INJECTION-%{matched_var_name}=%
    {tx.0}"

    SecRuleUpdateTargetByMsg "System Command Injection" !ARGS:email

The effective resulting rule in the previous example will append the
target to the end of the variable list as follows:

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/*|!ARGS:email "[\;\|\`]\W*?\bmail\b" \
         "phase:2,rev:'2.1.1',capture,t:none,t:htmlEntityDecode,t:compressWhitespace,t:lowercase,ctl:auditLogParts=+E,block,msg:'System Command Injection',id:'958895',tag:'WEB_ATTACK/COMMAND_INJECTION',tag:'WASCTC/WASC-31',tag:'OWASP_TOP_10/A1',tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.command_injection_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/COMMAND_INJECTION-%{matched_var_name}=%
    {tx.0}""

**Explicitly Replacing Targets**

You can also entirely replace the target list to something more
appropriate for your environment. For example, lets say you want to
inspect REQUEST_URI instead of REQUEST_FILENAME, you could do this:

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/* "[\;\|\`]\W*?\bmail\b" \
         "phase:2,rev:'2.1.1',capture,t:none,t:htmlEntityDecode,t:compressWhitespace,t:lowercase,ctl:auditLogParts=+E,block,msg:'System Command Injection',id:'958895',tag:'WEB_ATTACK/COMMAND_INJECTION',tag:'WASCTC/WASC-31',tag:'OWASP_TOP_10/A1',tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.command_injection_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/COMMAND_INJECTION-%{matched_var_name}=%
    {tx.0}"

    SecRuleUpdateTargetByMsg "System Command Injection" REQUEST_URI REQUEST_FILENAME

The effective resulting rule in the previous example will append the
target to the end of the variable list as follows:

    SecRule REQUEST_URI|ARGS_NAMES|ARGS|XML:/* "[\;\|\`]\W*?\bmail\b" \
         "phase:2,rev:'2.1.1',capture,t:none,t:htmlEntityDecode,t:compressWhitespace,t:lowercase,ctl:auditLogParts=+E,block,msg:'System Command Injection',id:'958895',tag:'WEB_ATTACK/COMMAND_INJECTION',tag:'WASCTC/WASC-31',tag:'OWASP_TOP_10/A1',tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.command_injection_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/COMMAND_INJECTION-%{matched_var_name}=%
    {tx.0}""

## SecRuleUpdateTargetByTag

**Description:** Updates the target (variable) list of the specified
rule by rule tag.

**Syntax:**
`SecRuleUpdateTargetByTag TEXT TARGET1[,TARGET2,TARGET3] REPLACED_TARGET`

**Example Usage:**
`SecRuleUpdateTargetByTag "WEB_ATTACK/XSS" "!ARGS:foo"`

**Scope:** Any

**Version:** 2.7-3.x

**Supported on libModSecurity:** Yes

This directive will append (or replace) variables to the current target
list of the specified rule with the targets provided in the second
parameter.

**Explicitly Appending Targets**

This is useful for implementing exceptions where you want to externally
update a target list to exclude inspection of specific variable(s).

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/* "[\;\|\`]\W*?\bmail\b" \
         "phase:2,rev:'2.1.1',capture,t:none,t:htmlEntityDecode,t:compressWhitespace,t:lowercase,ctl:auditLogParts=+E,block,msg:'System Command Injection',id:'958895',tag:'WEB_ATTACK/COMMAND_INJECTION',tag:'WASCTC/WASC-31',tag:'OWASP_TOP_10/A1',tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.command_injection_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/COMMAND_INJECTION-%{matched_var_name}=%
    {tx.0}"

    SecRuleUpdateTargetByTag "WASCTC/WASC-31" !ARGS:email

The effective resulting rule in the previous example will append the
target to the end of the variable list as follows:

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/*|!ARGS:email "[\;\|\`]\W*?\bmail\b" \
         "phase:2,rev:'2.1.1',capture,t:none,t:htmlEntityDecode,t:compressWhitespace,t:lowercase,ctl:auditLogParts=+E,block,msg:'System Command Injection',id:'958895',tag:'WEB_ATTACK/COMMAND_INJECTION',tag:'WASCTC/WASC-31',tag:'OWASP_TOP_10/A1',tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.command_injection_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/COMMAND_INJECTION-%{matched_var_name}=%
    {tx.0}""

**Explicitly Replacing Targets**

You can also entirely replace the target list to something more
appropriate for your environment. For example, lets say you want to
inspect REQUEST_URI instead of REQUEST_FILENAME, you could do this:

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/* "[\;\|\`]\W*?\bmail\b" \
         "phase:2,rev:'2.1.1',capture,t:none,t:htmlEntityDecode,t:compressWhitespace,t:lowercase,ctl:auditLogParts=+E,block,msg:'System Command Injection',id:'958895',tag:'WEB_ATTACK/COMMAND_INJECTION',tag:'WASCTC/WASC-31',tag:'OWASP_TOP_10/A1',tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.command_injection_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/COMMAND_INJECTION-%{matched_var_name}=%
    {tx.0}"

    SecRuleUpdateTargetByTag "WASCTC/WASC-31" REQUEST_URI REQUEST_FILENAME

The effective resulting rule in the previous example will append the
target to the end of the variable list as follows:

    SecRule REQUEST_URI|ARGS_NAMES|ARGS|XML:/* "[\;\|\`]\W*?\bmail\b" \
         "phase:2,rev:'2.1.1',capture,t:none,t:htmlEntityDecode,t:compressWhitespace,t:lowercase,ctl:auditLogParts=+E,block,msg:'System Command Injection',id:'958895',tag:'WEB_ATTACK/COMMAND_INJECTION',tag:'WASCTC/WASC-31',tag:'OWASP_TOP_10/A1',tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.command_injection_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/COMMAND_INJECTION-%{matched_var_name}=%
    {tx.0}""

## SecServerSignature

**Description:** Instructs ModSecurity to change the data presented in
the \"Server:\" response header token.

**Syntax:** `SecServerSignature "WEB SERVER SOFTWARE"`

**Example Usage:** `SecServerSignature "Microsoft-IIS/6.0"`

**Scope:** Main

**Version:** 2.0.0-2.9.x

**Supported on libModSecurity:** TBI

In order for this directive to work, you must set the Apache
ServerTokens directive to Full. ModSecurity will overwrite the server
signature data held in this memory space with the data set in this
directive. If ServerTokens is not set to Full, then the memory space is
most likely not large enough to hold the new data we are looking to
insert.

Note : This directive is not allowed inside VirtualHosts. If enabled, it must be placed in a global server-wide configuration file such as your default modsecurity.conf.

## SecStatusEngine

**Description:** Controls Status Reporting functionality. Uses DNS-based
reporting to send software version information to the ModSecurity
Project team.

**Syntax:** `SecStatusEngine On|Off`

**Example Usage:** `SecStatusEngine On`

**Scope:** Any

**Version:** 2.8.0-2.9.x

**Supported on libModSecurity:** TBI

**Default:** Off

If SecStatusEngine directive is not present, it is disabled. If
SecStatusEngine is marked as On, the following information will be
shared with the ModSecurity project team when the web server is started:

-   Anonymous unique id for the server
-   Version of:
    -   ModSecurity
    -   Web Server Software (Apache, IIS, Nginx, Java)
    -   APR
    -   Libxml2
    -   Lua
    -   PCRE

Note : This is an example of the information presented in the Apache error_log representing what data will be sent:

```{=html}
<!-- -->
```
    [Mon Jan 20 10:55:22.001020 2014] [:notice] [pid 18231:tid 140735189168512] ModSecurity: StatusEngine call: "2.7.7,Apache/2.4.4 (Unix),1.4.6/1.4.6, 8.32 /8.32 2012-11-30,Lua 5.1/(null),2.7.8/(null),96ce9ba3c2fb71f7a8bb92a88d560d44dbe459b8"
    [Mon Jan 20 10:55:22.089012 2014] [:notice] [pid 18231:tid 140735189168512] ModSecurity: StatusEngine call successfully submitted.

## SecStreamInBodyInspection

**Description:** Configures the ability to use stream inspection for
inbound request data in a re-allocable buffer. For security reasons we
are still buffering the stream.

**Syntax:** `SecStreamInBodyInspection On|Off`

**Example Usage:** `SecStreamInBodyInspection On`

**Scope:** Any

**Version:** 2.6.0-2.9.x

**Default:** Off

**Supported on libModSecurity:** No

This feature enables the creation of the STREAM_INPUT_BODY variable and
is useful for data modification or to match data in raw data for any
content-types.

Note : This directive provides full access to REQUEST_BODY payload data. It does not include REQUEST_URI or REQUEST_HEADER data. Also it provides data to all kind of content types, different than REQUEST_BODY.

```{=html}
<!-- -->
```

Note : This directive is NOT supported for libModSecurity (v3). Naturally, STREAM_INPUT_BODY is also NOT supported on libModSecurity.

```{=html}
<!-- -->
```

Note : This directive may significantly impact file upload times. The impact depends on server resources and the nature of operations being performed on the request bodies being streamed in.

## SecStreamOutBodyInspection

**Description:** Configures the ability to use stream inspection for
outbound request data in a re-allocable buffer. For security reasons we
are still buffering the stream.

**Syntax:** `SecStreamOutBodyInspection On|Off`

**Example Usage:** `SecStreamOutBodyInspection On`

**Scope:** Any

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBD

**Default:** Off

This feature enables the creation of the STREAM_OUTPUT_BODY variable and
is useful when you need to do data modification into response body.

Note : This directive provides access to RESPONSE_BODY payload data. It does not include RESPONSE_HEADER data.

## SecTmpDir

**Description:** Configures the directory where temporary files will be
created.

**Syntax:** `SecTmpDir /path/to/dir`

**Example Usage:** `SecTmpDir /tmp`

**Scope:** Any

**Version:** 2.0.0-2.9.x

**Supported on libModSecurity:** No

The location specified needs to be writable by the Apache user process.
This is the directory location where ModSecurity will swap data to disk
if it runs out of memory (more data than what was specified in the
SecRequestBodyInMemoryLimit directive) during inspection.

As of ModSecurity version 3.0, SecTmpDir is no longer supported.
libModSecurity is able to deal with request body in a file or in a
buffer (chunked or not). Web servers have properties which controls
whenever a request should be saved to a file or used as a buffer (e.g.
client_body_buffer_size
<https://nginx.org/en/docs/http/ngx_http_core_module.html#client_body_buffer_size>)
. If it is a file, ModSecurity will use the file to perform the
inspection. If not, the buffer will be used.

## SecUnicodeMapFile

**Description:** Defines the path to the file that will be used by the
urlDecodeUni transformation function to map Unicode code points during
normalization and specifies the Code Point to use.

**Syntax:** `SecUnicodeMapFile /path/to/unicode.mapping CODEPOINT`

**Example Usage:** `SecUnicodeMapFile unicode.mapping 20127`

**Scope:** Any

**Version:** 2.6.1-2.9.x

**Supported on libModSecurity:** TBI

## SecUnicodeCodePage

**Description:** Defines which Unicode code point will be used by the
urlDecodeUni transformation function during normalization.

**Syntax:** `SecUnicodeCodePage XXXXX`

**Example Usage:** `SecUnicodeCodePage 20127`

**Scope:** Any

**Version:** 2.6.1 - DEPRECATED

**Supported on libModSecurity:** No (Deprecated)

## SecUploadDir

**Description:** Configures the directory where intercepted files will
be stored.

**Syntax:** `SecUploadDir /path/to/dir`

**Example Usage:** `SecUploadDir /tmp`

**Scope:** Any

**Version:** 2.0.0-3.x

**Supported on libModSecurity:** Yes

This directory must be on the same filesystem as the temporary directory
defined with SecTmpDir. This directive is used with SecUploadKeepFiles.

## SecUploadFileLimit

**Description:** Configures the maximum number of file uploads processed
in a multipart POST.

**Syntax:** `SecUploadFileLimit number`

**Example Usage:** `SecUploadFileLimit 10`

**Scope:** Any

**Version:** 2.5.12-3.x

**Supported on libModSecurity:** Yes

The default is set to 100 files, but you are encouraged to reduce this
value. Any file over the limit will not be extracted and the
MULTIPART_FILE_LIMIT_EXCEEDED and MULTIPART_STRICT_ERROR flags will be
set. To prevent bypassing any file checks, you must check for one of
these flags.

Note : If the limit is exceeded, the part name and file name will still be recorded in FILES_NAME and FILES, the file size will be recorded in FILES_SIZES, but there will be no record in FILES_TMPNAMES as a temporary file was not created.

## SecUploadFileMode

**Description:** Configures the mode (permissions) of any uploaded files
using an octal mode (as used in chmod).

**Syntax:** `SecUploadFileMode octal_mode|"default"`

**Example Usage:** `SecUploadFileMode 0640`

**Scope:** Any

**Version:** 2.1.6

**Supported on libModSecurity:** Yes

This feature is not available on operating systems not supporting octal
file modes. The default mode (0600) only grants read/write access to the
account writing the file. If access from another account is needed
(using clamd is a good example), then this directive may be required.
However, use this directive with caution to avoid exposing potentially
sensitive data to unauthorized users. Using the value \"default\" will
revert back to the default setting.

Note : The process umask may still limit the mode if it is being more restrictive than the mode set using this directive.

## SecUploadKeepFiles

**Description:** Configures whether or not the intercepted files will be
kept after transaction is processed.

**Syntax:** `SecUploadKeepFiles On|Off|RelevantOnly`

**Example Usage:** `SecUploadKeepFiles On`

**Scope:** Any

**Version:** 2.0.0

**Supported on libModSecurity:** Yes

This directive requires the storage directory to be defined (using
SecUploadDir).

Possible values are:

-   **On** - Keep uploaded files.
-   **Off** - Do not keep uploaded files.
-   **RelevantOnly** - This will keep only those files that belong to
    requests that are deemed relevant.

Note : RelevantOnly is not yet supported on libModSecurity

## SecWebAppId

**Description:** Creates an application namespace, allowing for separate
persistent session and user storage.

**Syntax:** `SecWebAppId "NAME"`

**Example Usage:** `SecWebAppId "WebApp1"`

**Scope:** Any

**Version:** 2.0.0-3.x

**Supported on libModSecurity:** Yes

**Default:** default

Application namespaces are used to avoid collisions between session IDs
and user IDs when multiple applications are deployed on the same server.
If it isn't used, a collision between session IDs might occur.

    <VirtualHost *:80> 
    ServerName app1.example.com 
    SecWebAppId "App1" ...
    </VirtualHost>

    <VirtualHost *:80> 
    ServerName app2.example.com 
    SecWebAppId "App2" ...
    </VirtualHost>

In the two examples configurations shown, SecWebAppId is being used in
conjunction with the Apache VirtualHost directives. Applications
namespace information is also recorded in the audit logs (using the
WebApp-Info header of the H part).

## SecXmlExternalEntity

**Description:** Enable or Disable the loading process of xml external
entity. Loading external entity without correct verifying process can
lead to a security issue.

**Syntax:** `SecXmlExternalEntity On|Off`

**Example Usage:** `SecXmlExternalEntity Off`

**Scope:** Any

**Version:** 2.7.3

**Supported on libModSecurity:** Yes

**Default:** default is Off

**NOTE:** You must enable this directive if you need to use the
`@validateSchema` or `@validateDtd` operators.

# Processing Phases {#processing_phases}

ModSecurity 2.x allows rules to be placed in one of the following five
phases of the Apache request cycle:

-   Request headers (REQUEST_HEADERS)
-   Request body (REQUEST_BODY)
-   Response headers (RESPONSE_HEADERS)
-   Response body (RESPONSE_BODY)
-   Logging (LOGGING)

Below is a diagram of the standard Apache Request Cycle. In the diagram,
the 5 ModSecurity processing phases are shown.

<http://www.modsecurity.org/graphics/modsec-rotation.jpg>

In order to select the phase a rule executes during, use the phase
action either directly in the rule or in using the SecDefaultAction
directive:

    SecDefaultAction "log,pass,phase:2,id:4"
    SecRule REQUEST_HEADERS:Host "!^$" "deny,phase:1,id:5"

Note : The data available in each phase is cumulative. This means that as you move onto later phases, you have access to more and more data from the transaction.\
Note : Keep in mind that rules are executed according to phases, so even if two rules are adjacent in a configuration file, but are set to execute in different phases, they would not happen one after the other. The order of rules in the configuration file is important only within the rules of each phase. This is especially important when using the skip and skipAfter actions.

```{=html}
<!-- -->
```

Note : The LOGGING phase is special. It is executed at the end of each transaction no matter what happened in the previous phases. This means it will be processed even if the request was intercepted or the allow action was used to pass the transaction through.

## Phase Request Headers {#phase_request_headers}

Rules in this phase are processed immediately after Apache completes
reading the request headers (post-read-request phase). At this point the
request body has not been read yet, meaning not all request arguments
are available. Rules should be placed in this phase if you need to have
them run early (before Apache does something with the request), to do
something before the request body has been read, determine whether or
not the request body should be buffered, or decide how you want the
request body to be processed (e.g. whether to parse it as XML or not).

Note : Rules in this phase can not leverage Apache scope directives (Directory, Location, LocationMatch, etc\...) as the post-read-request hook does not have this information yet. The exception here is the VirtualHost directive. If you want to use ModSecurity rules inside Apache locations, then they should run in Phase 2. Refer to the Apache Request Cycle/ModSecurity Processing Phases diagram.

## Phase Request Body {#phase_request_body}

This is the general-purpose input analysis phase. Most of the
application-oriented rules should go here. In this phase you are
guaranteed to have received the request arguments (provided the request
body has been read). ModSecurity supports three encoding types for the
request body phase:

-   **application/x-www-form-urlencoded** - used to transfer form data
-   **multipart/form-data** - used for file transfers
-   **text/xml** - used for passing XML data

Other encodings are not used by most web applications.

Note : In order to access the Request Body phase data, you must have SecRequestBodyAccess set to On.

## Phase Response Headers {#phase_response_headers}

This phase takes place just before response headers are sent back to the
client. Run here if you want to observe the response before that
happens, and if you want to use the response headers to determine if you
want to buffer the response body. Note that some response status codes
(such as 404) are handled earlier in the request cycle by Apache and my
not be able to be triggered as expected. Additionally, there are some
response headers that are added by Apache at a later hook (such as Date,
Server and Connection) that we would not be able to trigger on or
sanitize. This should work appropriately in a proxy setup or within
phase:5 (logging).

## Phase Response Body {#phase_response_body}

This is the general-purpose output analysis phase. At this point you can
run rules against the response body (provided it was buffered, of
course). This is the phase where you would want to inspect the outbound
HTML for information disclosure, error messages or failed authentication
text.

Note : In order to access the Response Body phase data, you must have SecResponseBodyAccess set to On

## Phase Logging {#phase_logging}

This phase is run just before logging takes place. The rules placed into
this phase can only affect how the logging is performed. This phase can
be used to inspect the error messages logged by Apache. You cannot
deny/block connections in this phase as it is too late. This phase also
allows for inspection of other response headers that weren\'t available
during phase:3 or phase:4. Note that you must be careful not to inherit
a disruptive action into a rule in this phase as this is a configuration
error in ModSecurity 2.5.0 and later versions

# Variables

The following variables are supported in ModSecurity 2.x:

## ARGS

ARGS is a collection and can be used on its own (means all arguments
including the POST Payload), with a static parameter (matches arguments
with that name), or with a regular expression (matches all arguments
with name that matches the regular expression). To look at only the
query string or body arguments, see the ARGS_GET and ARGS_POST
collections.

Some variables are actually collections, which are expanded into more
variables at runtime. The following example will examine all request
arguments:

`SecRule ARGS dirty "id:7"`

Sometimes, however, you will want to look only at parts of a collection.
This can be achieved with the help of the selection operator(colon). The
following example will only look at the arguments named p (do note that,
in general, requests can contain multiple arguments with the same name):

`SecRule ARGS:p dirty "id:8"`

It is also possible to specify exclusions. The following will examine
all request arguments for the word dirty, except the ones named z
(again, there can be zero or more arguments named z):

`SecRule ARGS|!ARGS:z dirty "id:9"`

There is a special operator that allows you to count how many variables
there are in a collection. The following rule will trigger if there is
more than zero arguments in the request (ignore the second parameter for
the time being):

`SecRule &ARGS !^0$ "id:10"`

And sometimes you need to look at an array of parameters, each with a
slightly different name. In this case you can specify a regular
expression in the selection operator itself. The following rule will
look into all arguments whose names begin with id\_:

`SecRule ARGS:/^id_/ dirty "id:11"`

Note : Using ARGS:p will not result in any invocations against the operator if argument p does not exist.

In ModSecurity 1.X, the ARGS variable stood for QUERY_STRING +
POST_PAYLOAD, whereas now it expands to individual variables.

## ARGS_COMBINED_SIZE

Contains the combined size of all request parameters. Files are excluded
from the calculation. This variable can be useful, for example, to
create a rule to ensure that the total size of the argument data is
below a certain threshold. The following rule detects a request whose
para- meters are more than 2500 bytes long:

`SecRule ARGS_COMBINED_SIZE "@gt 2500" "id:12"`

## ARGS_GET

ARGS_GET is similar to ARGS, but contains only query string parameters.

## ARGS_GET_NAMES

ARGS_GET_NAMES is similar to ARGS_NAMES, but contains only the names of
query string parameters.

## ARGS_NAMES

Contains all request parameter names. You can search for specific
parameter names that you want to inspect. In a positive policy scenario,
you can also whitelist (using an inverted rule with the exclamation
mark) only the authorized argument names. This example rule allows only
two argument names: p and a:

`SecRule ARGS_NAMES "!^(p|a)$" "id:13"`

## ARGS_POST

ARGS_POST is similar to ARGS, but only contains arguments from the POST
body.

## ARGS_POST_NAMES

ARGS_POST_NAMES is similar to ARGS_NAMES, but contains only the names of
request body parameters.

## AUTH_TYPE

This variable holds the authentication method used to validate a user,
if any of the methods built into HTTP are used. In a reverse-proxy
deployment, this information will not be available if the authentication
is handled in the backend web server.

`SecRule AUTH_TYPE "Basic" "id:14"`

## DURATION

Contains the number of milliseconds elapsed since the beginning of the
current transaction. Available starting with 2.6.0.

Note : Starting with ModSecurity 2.7.0 the time is microseconds.

## ENV

Collection that provides access to environment variables set by
ModSecurity or other server modules. Requires a single parameter to
specify the name of the desired variable.

    # Set environment variable 
    SecRule REQUEST_FILENAME "printenv" \
    "phase:2,id:15,pass,setenv:tag=suspicious" 

    # Inspect environment variable
    SecRule ENV:tag "suspicious" "id:16"

    # Reading an environment variable from other Apache module (mod_ssl)
    SecRule TX:ANOMALY_SCORE "@gt 0" "phase:5,id:16,msg:'%{env.ssl_cipher}'"

Note : Use setenv to set environment variables to be accessed by Apache.

## FILES

Contains a collection of original file names (as they were called on the
remote user's filesys- tem). Available only on inspected
multipart/form-data requests.

`SecRule FILES "@rx \.conf$" "id:17"`

Note : Only available if files were extracted from the request body.

## FILES_COMBINED_SIZE

Contains the total size of the files transported in request body.
Available only on inspected multipart/form-data requests.

`SecRule FILES_COMBINED_SIZE "@gt 100000" "id:18"`

## FILES_NAMES

Contains a list of form fields that were used for file upload. Available
only on inspected multipart/form-data requests.

`SecRule FILES_NAMES "^upfile$" "id:19"`

## FULL_REQUEST

Contains the complete request: Request line, Request headers and Request
body (if any). The last available only if SecRequestBodyAccess was set
to On. Note that all properties of SecRequestBodyAccess will be
respected here, such as: SecRequestBodyLimit.

`SecRule FULL_REQUEST "User-Agent: ModSecurity Regression Tests" "id:21"`

Note : Available on version 2.8.0+

## FULL_REQUEST_LENGTH

Represents the amount of bytes that FULL_REQUEST may use.

`SecRule FULL_REQUEST_LENGTH "@eq 205" "id:21"`

Note : Available on version 2.8.0+

## FILES_SIZES

Contains a list of individual file sizes. Useful for implementing a size
limitation on individual uploaded files. Available only on inspected
multipart/form-data requests.

`SecRule FILES_SIZES "@gt 100" "id:20"`

## FILES_TMPNAMES

Contains a list of temporary files' names on the disk. Useful when used
together with \@inspectFile. Available only on inspected
multipart/form-data requests.

`SecRule FILES_TMPNAMES "@inspectFile /path/to/inspect_script.pl" "id:21"`

## FILES_TMP_CONTENT

Contains a key-value set where value is the content of the file which
was uploaded. Useful when used together with \@fuzzyHash.

`SecRule FILES_TMP_CONTENT "@fuzzyHash $ENV{CONF_DIR}/ssdeep.txt 1" "id:192372,log,deny"`

Note : Available on version 2.9.0-RC1+\
Note II : SecUploadKeepFiles should be set to \'On\' in order to have this collection filled.

## GEO

GEO is a collection populated by the results of the last \@geoLookup
operator. The collection can be used to match geographical fields looked
from an IP address or hostname.

Available since ModSecurity 2.5.0.

Fields:

-   COUNTRY_CODE: Two character country code. EX: US, GB, etc.
-   COUNTRY_CODE3: Up to three character country code.
-   COUNTRY_NAME: The full country name.
-   COUNTRY_CONTINENT: The two character continent that the country is
    located. EX: EU
-   REGION: The two character region. For US, this is state. For Canada,
    providence, etc.
-   CITY: The city name if supported by the database.
-   POSTAL_CODE: The postal code if supported by the database.
-   LATITUDE: The latitude if supported by the database.
-   LONGITUDE: The longitude if supported by the database.
-   DMA_CODE: The metropolitan area code if supported by the database.
    (US only)
-   AREA_CODE: The phone system area code. (US only)

Example:

    SecGeoLookupDb /usr/local/geo/data/GeoLiteCity.dat
    ...
    SecRule REMOTE_ADDR "@geoLookup" "chain,id:22,drop,msg:'Non-GB IP address'"
    SecRule GEO:COUNTRY_CODE "!@streq GB"

## HIGHEST_SEVERITY

This variable holds the highest severity of any rules that have matched
so far. Severities are numeric values and thus can be used with
comparison operators such as \@lt, and so on. A value of 255 indicates
that no severity has been set.

`SecRule HIGHEST_SEVERITY "@le 2" "phase:2,id:23,deny,status:500,msg:'severity %{HIGHEST_SEVERITY}'"`

Note : Higher severities have a lower numeric value.

## INBOUND_DATA_ERROR

This variable will be set to 1 when the request body size is above the
setting configured by SecRequestBodyLimit directive. Your policies
should always contain a rule to check this variable. Depending on the
rate of false positives and your default policy you should decide
whether to block or just warn when the rule is triggered.

The best way to use this variable is as in the example below:

`SecRule INBOUND_DATA_ERROR "@eq 1" "phase:2,id:24,t:none,log,pass,msg:'Request Body Larger than SecRequestBodyLimit Setting'"`

## MATCHED_VAR

This variable holds the value of the most-recently matched variable. It
is similar to the TX:0, but it is automatically supported by all
operators and there is no need to specify the capture action.

    SecRule ARGS pattern chain,deny,id:25
      SecRule MATCHED_VAR "further scrutiny"

Note : Be aware that this variable holds data for the ***last*** operator match. This means that if there are more than one matches, only the last one will be populated. Use MATCHED_VARS variable if you want all matches.

## MATCHED_VARS

Similar to MATCHED_VAR except that it is a collection of ***all
matches*** for the current operator check.

    SecRule ARGS pattern "chain,deny,id:26"
      SecRule MATCHED_VARS "@eq ARGS:param"

## MATCHED_VAR_NAME

This variable holds the full name of the variable that was matched
against.

    SecRule ARGS pattern "chain,deny,id:27"
      SecRule MATCHED_VAR_NAME "@eq ARGS:param"

Note : Be aware that this variable holds data for the ***last*** operator match. This means that if there are more than one matches, only the last one will be populated. Use MATCHED_VARS_NAMES variable if you want all matches.

## MATCHED_VARS_NAMES

Similar to MATCHED_VAR_NAME except that it is a collection of ***all
matches*** for the current operator check.

    SecRule ARGS pattern "chain,deny,id:28"
      SecRule MATCHED_VARS_NAMES "@eq ARGS:param"

## MODSEC_BUILD

This variable holds the ModSecurity build number. This variable is
intended to be used to check the build number prior to using a feature
that is available only in a certain build. Example:

    SecRule MODSEC_BUILD "!@ge 02050102" "skipAfter:12345,id:29"
    SecRule ARGS "@pm some key words" "id:12345,deny,status:500"

## MULTIPART_CRLF_LF_LINES

This flag variable will be set to 1 whenever a multi-part request uses
mixed line terminators. The multipart/form-data RFC requires CRLF
sequence to be used to terminate lines. Since some client
implementations use only LF to terminate lines you might want to allow
them to proceed under certain circumstances (if you want to do this you
will need to stop using MULTIPART_STRICT_ERROR and check each multi-part
flag variable individually, avoiding MULTIPART_LF_LINE). However, mixing
CRLF and LF line terminators is dangerous as it can allow for evasion.
Therefore, in such cases, you will have to add a check for
MULTIPART_CRLF_LF_LINES.

## MULTIPART_FILENAME

## MULTIPART_NAME

This variable contains the multipart data from field NAME.

## MULTIPART_PART_HEADERS

This variable is a collection of all part headers found within the
request body with Content-Type multipart/form-data. The key of each item
in the collection is the name of the part in which it was found, while
the value is the entire part-header line \-- including both the
part-header name and the part-header value.

`SecRule MULTIPART_PART_HEADERS:parm1 "@rx content-type:.*jpeg" "phase:2,deny,status:403,id:500074,t:lowercase"`

Note: Available in v2.9.6 and later.

## MULTIPART_STRICT_ERROR

MULTIPART_STRICT_ERROR will be set to 1 when any of the following
variables is also set to 1: REQBODY_PROCESSOR_ERROR,
MULTIPART_BOUNDARY_QUOTED, MULTIPART_BOUNDARY_WHITESPACE,
MULTIPART_DATA_BEFORE, MULTIPART_DATA_AFTER, MULTIPART_HEADER_FOLDING,
MULTIPART_LF_LINE, MULTIPART_MISSING_SEMICOLON MULTIPART_INVALID_QUOTING
MULTIPART_INVALID_HEADER_FOLDING MULTIPART_FILE_LIMIT_EXCEEDED. Each of
these variables covers one unusual (although sometimes legal) aspect of
the request body in multipart/form-data format. Your policies should
always contain a rule to check either this variable (easier) or one or
more individual variables (if you know exactly what you want to
accomplish). Depending on the rate of false positives and your default
policy you should decide whether to block or just warn when the rule is
triggered.

The best way to use this variable is as in the example below:

    SecRule MULTIPART_STRICT_ERROR "!@eq 0" \
    "phase:2,id:30,t:none,log,deny,msg:'Multipart request body \
    failed strict validation: \
    PE %{REQBODY_PROCESSOR_ERROR}, \
    BQ %{MULTIPART_BOUNDARY_QUOTED}, \
    BW %{MULTIPART_BOUNDARY_WHITESPACE}, \
    DB %{MULTIPART_DATA_BEFORE}, \
    DA %{MULTIPART_DATA_AFTER}, \
    HF %{MULTIPART_HEADER_FOLDING}, \
    LF %{MULTIPART_LF_LINE}, \
    SM %{MULTIPART_MISSING_SEMICOLON}, \
    IQ %{MULTIPART_INVALID_QUOTING}, \
    IQ %{MULTIPART_INVALID_HEADER_FOLDING}, \
    FE %{MULTIPART_FILE_LIMIT_EXCEEDED}'"

The multipart/form-data parser was upgraded in ModSecurity v2.1.3 to
actively look for signs of evasion. Many variables (as listed above)
were added to expose various facts discovered during the parsing
process. The MULTIPART_STRICT_ERROR variable is handy to check on all
abnormalities at once. The individual variables allow detection to be
fine-tuned according to your circumstances in order to reduce the number
of false positives.

## MULTIPART_UNMATCHED_BOUNDARY

Set to 1 when, during the parsing phase of a multipart/request-body,
ModSecurity encounters what feels like a boundary but it is not. Such an
event may occur when evasion of ModSecurity is attempted.

The best way to use this variable is as in the example below:

    SecRule MULTIPART_UNMATCHED_BOUNDARY "!@eq 0" \
    "phase:2,id:31,t:none,log,deny,msg:'Multipart parser detected a possible unmatched boundary.'"

Change the rule from blocking to logging-only if many false positives
are encountered.

## OUTBOUND_DATA_ERROR

This variable will be set to 1 when the response body size is above the
setting configured by SecResponseBodyLimit directive. Your policies
should always contain a rule to check this variable. Depending on the
rate of false positives and your default policy you should decide
whether to block or just warn when the rule is triggered.

The best way to use this variable is as in the example below:

`SecRule OUTBOUND_DATA_ERROR "@eq 1" "phase:1,id:32,t:none,log,pass,msg:'Response Body Larger than SecResponseBodyLimit Setting'"`

## PATH_INFO

Contains the extra request URI information, also known as path info.
(For example, in the URI /index.php/123, /123 is the path info.)
Available only in embedded deployments.

`SecRule PATH_INFO "^/(bin|etc|sbin|opt|usr)" "id:33"`

## PERF_ALL

This special variable contains a string that's a combination of all
other performance variables, arranged in the same order in which they
appear in the Stopwatch2 audit log header. It's intended for use in
custom Apache logs

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBI

## PERF_COMBINED

Contains the time, in microseconds, spent in ModSecurity during the
current transaction. The value in this variable is arrived to by adding
all the performance variables except PERF_SREAD (the time spent reading
from persistent storage is already included in the phase measurements).

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBI

## PERF_GC

Contains the time, in microseconds, spent performing garbage collection.

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBI

## PERF_LOGGING

Contains the time, in microseconds, spent in audit logging. This value
is known only after the handling of a transaction is finalized, which
means that it can only be logged using mod_log_config and the
%{VARNAME}M syntax.

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBI

## PERF_PHASE1

Contains the time, in microseconds, spent processing phase 1.

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBI

## PERF_PHASE2

Contains the time, in microseconds, spent processing phase 2.

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBI

## PERF_PHASE3

Contains the time, in microseconds, spent processing phase 3.

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBI

## PERF_PHASE4

Contains the time, in microseconds, spent processing phase 4.

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBI

## PERF_PHASE5

Contains the time, in microseconds, spent processing phase 5.

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBI

## PERF_RULES

PERF_RULES is a collection, that is populated with the rules hitting the
performance threshold defined with SecRulePerfTime. The collection
contains the time, in microseconds, spent processing the individual
rule. The various items in the collection can be accessed via the rule
id.

**Version:** 2.7.0-2.9.x

**Supported on libModSecurity:** TBI

    SecRulePerfTime            100

    SecRule FILES_TMPNAMES "@inspectFile /path/to/util/runav.pl" \
      "phase:2,id:10001,deny,log,msg:'Virus scan detected an error.'"

    SecRule   &PERF_RULES "@eq 0"    "phase:5,id:95000,\
      pass,log,msg:'All rules performed below processing time limit.'"
    SecRule   PERF_RULES  "@ge 1000" "phase:5,id:95001,pass,log,\
      msg:'Rule %{MATCHED_VAR_NAME} spent at least 1000 usec.'"
    SecAction "phase:5,id:95002,pass,log, msg:'File inspection took %{PERF_RULES.10001} usec.'"

The rule with id 10001 defines an external file inspection rule. The
rule with id 95000 checks the size of the PERF_RULES collection. If the
collection is empty, it writes a note in the logfile. Rule 95001 is
executed for every item in the PERF_RULES collection. Every item is thus
being checked against the limit of 1000 microseconds. If the rule spent
at least that amount of time, then a note containing the rule id is
being written to the logfile. The final rule 95002 notes the time spent
in rule 10001 (the virus inspection).

## PERF_SREAD

Contains the time, in microseconds, spent reading from persistent
storage.

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBI

## PERF_SWRITE

Contains the time, in microseconds, spent writing to persistent storage.

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBI

## QUERY_STRING

Contains the query string part of a request URI. The value in
QUERY_STRING is always provided raw, without URL decoding taking place.

`SecRule QUERY_STRING "attack" "id:34"`

## REMOTE_ADDR

This variable holds the IP address of the remote client.

`SecRule REMOTE_ADDR "@ipMatch 192.168.1.101" "id:35"`

## REMOTE_HOST

If the Apache directive HostnameLookups is set to On, then this variable
will hold the remote hostname resolved through DNS. If the directive is
set to Off, this variable it will hold the remote IP address (same as
REMOTE_ADDR). Possible uses for this variable would be to deny known bad
client hosts or network blocks, or conversely, to allow in authorized
hosts.

`SecRule REMOTE_HOST "\.evil\.network\org$" "id:36"`

## REMOTE_PORT

This variable holds information on the source port that the client used
when initiating the connection to our web server.

In the following example, we are evaluating to see whether the
REMOTE_PORT is less than 1024, which would indicate that the user is a
privileged user:

`SecRule REMOTE_PORT "@lt 1024" "id:37"`

## REMOTE_USER

This variable holds the username of the authenticated user. If there are
no password access controls in place (Basic or Digest authentication),
then this variable will be empty.

`SecRule REMOTE_USER "@streq admin" "id:38"`

Note : In a reverse-proxy deployment, this information will not be available if the authentication is handled in the backend web server.

## REQBODY_ERROR

Contains the status of the request body processor used for request body
parsing. The values can be 0 (no error) or 1 (error). This variable will
be set by request body processors (typically the multipart/request-data
parser, JSON or the XML parser) when they fail to do their work.

`SecRule REQBODY_ERROR "@eq 1" deny,phase:2,id:39`

Note : Your policies must have a rule to check for request body processor errors at the very beginning of phase 2. Failure to do so will leave the door open for impedance mismatch attacks. It is possible, for example, that a payload that cannot be parsed by ModSecurity can be successfully parsed by more tolerant parser operating in the application. If your policy dictates blocking, then you should reject the request if error is detected. When operating in detection-only mode, your rule should alert with high severity when request body processing fails.

```{=html}
<!-- -->
```

Related issues: #1475

## REQBODY_ERROR_MSG

If there's been an error during request body parsing, the variable will
contain the following error message:

`SecRule REQBODY_ERROR_MSG "failed to parse" "id:40"`

## REQBODY_PROCESSOR

Contains the name of the currently used request body processor. The
possible values are URLENCODED, MULTIPART, and XML.

    SecRule REQBODY_PROCESSOR "^XML$ chain,id:41 
      SecRule XML "@validateDTD /opt/apache-frontend/conf/xml.dtd"

## REQUEST_BASENAME

This variable holds just the filename part of REQUEST_FILENAME (e.g.,
index.php).

`SecRule REQUEST_BASENAME "^login\.php$" phase:2,id:42,t:none,t:lowercase`

Note : Please note that anti-evasion transformations are not applied to this variable by default. REQUEST_BASENAME will recognise both / and \\ as path separators. You should understand that the value of this variable depends on what was provided in request, and that it does not have to correspond to the resource (on disk) that will be used by the web server.

## REQUEST_BODY

Holds the raw request body. This variable is available only if the
URLENCODED request body processor was used, which will occur by default
when the application/x-www-form-urlencoded content type is detected, or
if the use of the URLENCODED request body parser was forced.

`SecRule REQUEST_BODY "^username=\w{25,}\&password=\w{25,}\&Submit\=login$" "id:43"`

As of 2.5.7, it is possible to force the presence of the REQUEST_BODY
variable, but only when there is no request body processor defined using
the ctl:forceRequestBodyVariable option in the REQUEST_HEADERS phase.

## REQUEST_BODY_LENGTH

Contains the number of bytes read from a request body. Available
starting with v2.6

## REQUEST_COOKIES

This variable is a collection of all of request cookies (values only).
Example: the following example is using the Ampersand special operator
to count how many variables are in the collection. In this rule, it
would trigger if the request does not include any Cookie headers.

`SecRule &REQUEST_COOKIES "@eq 0" "id:44"`

## REQUEST_COOKIES_NAMES

This variable is a collection of the names of all request cookies. For
example, the following rule will trigger if the JSESSIONID cookie is not
present:

`SecRule &REQUEST_COOKIES_NAMES:JSESSIONID "@eq 0" "id:45"`

## REQUEST_FILENAME

This variable holds the relative request URL without the query string
part (e.g., /index.php).

`SecRule REQUEST_FILENAME "^/cgi-bin/login\.php$" phase:2,id:46,t:none,t:normalizePath`

Note : Please note that anti-evasion transformations are not used on REQUEST_FILENAME, which means that you will have to specify them in the rules that use this variable.

## REQUEST_HEADERS

This variable can be used as either a collection of all of the request
headers or can be used to inspect selected headers (by using the
REQUEST_HEADERS:Header-Name syntax).

`SecRule REQUEST_HEADERS:Host "^[\d\.]+$" "deny,id:47,log,status:400,msg:'Host header is a numeric IP address'"`

Note: ModSecurity will treat multiple headers that have identical names in accordance with how the webserver treats them. For Apache this means that they will all be concatenated into a single header with a comma as the deliminator.

## REQUEST_HEADERS_NAMES

This variable is a collection of the names of all of the request
headers.

`SecRule REQUEST_HEADERS_NAMES "^x-forwarded-for" "log,deny,id:48,status:403,t:lowercase,msg:'Proxy Server Used'"`

## REQUEST_LINE

This variable holds the complete request line sent to the server
(including the request method and HTTP version information).

    # Allow only POST, GET and HEAD request methods, as well as only
    # the valid protocol versions 
    SecRule REQUEST_LINE "!(^((?:(?:POS|GE)T|HEAD))|HTTP/(0\.9|1\.0|1\.1)$)" "phase:1,id:49,log,block,t:none"

## REQUEST_METHOD

This variable holds the request method used in the transaction.

`SecRule REQUEST_METHOD "^(?:CONNECT|TRACE)$" "id:50,t:none"`

## REQUEST_PROTOCOL

This variable holds the request protocol version information.

`SecRule REQUEST_PROTOCOL "!^HTTP/(0\.9|1\.0|1\.1)$" "id:51"`

## REQUEST_URI

This variable holds the full request URL including the query string data
(e.g., /index.php? p=X). However, it will never contain a domain name,
even if it was provided on the request line.

`SecRule REQUEST_URI "attack" "phase:1,id:52,t:none,t:urlDecode,t:lowercase,t:normalizePath"`

Note : Please note that anti-evasion transformations are not used on REQUEST_URI, which means that you will have to specify them in the rules that use this variable.

## REQUEST_URI_RAW

Same as REQUEST_URI but will contain the domain name if it was provided
on the request line (e.g., <http://www.example.com/index.php?p=X>).

`SecRule REQUEST_URI_RAW "`[`http:/`](http:/)`" "phase:1,id:53,t:none,t:urlDecode,t:lowercase,t:normalizePath"`

Note : Please note that anti-evasion transformations are not used on REQUEST_URI_RAW, which means that you will have to specify them in the rules that use this variable.

## RESPONSE_BODY

This variable holds the data for the response body, but only when
response body buffering is enabled.

`SecRule RESPONSE_BODY "ODBC Error Code" "phase:4,id:54,t:none"`

## RESPONSE_CONTENT_LENGTH

Response body length in bytes. Can be available starting with phase 3,
but it does not have to be (as the length of response body is not always
known in advance). If the size is not known, this variable will contain
a zero. If RESPONSE_CONTENT_LENGTH contains a zero in phase 5 that means
the actual size of the response body was 0. The value of this variable
can change between phases if the body is modified. For example, in
embedded mode, mod_deflate can compress the response body between phases
4 and 5.

## RESPONSE_CONTENT_TYPE

Response content type. Available only starting with phase 3. The value
available in this variable is taken directly from the internal
structures of Apache, which means that it may contain the information
that is not yet available in response headers. In embedded deployments,
you should always refer to this variable, rather than to
RESPONSE_HEADERS:Content-Type.

## RESPONSE_HEADERS

This variable refers to response headers, in the same way as
REQUEST_HEADERS does to request headers.

`SecRule RESPONSE_HEADERS:X-Cache "MISS" "id:55"`

This variable may not have access to some headers when running in
embedded mode. Headers such as Server, Date, Connection, and
Content-Type could be added just prior to sending the data to the
client. This data should be available in phase 5 or when deployed in
proxy mode.

## RESPONSE_HEADERS_NAMES

This variable is a collection of the response header names.

`SecRule RESPONSE_HEADERS_NAMES "Set-Cookie" "phase:3,id:56,t:none"`

The same limitations apply as the ones discussed in RESPONSE_HEADERS.

## RESPONSE_PROTOCOL

This variable holds the HTTP response protocol information.

`SecRule RESPONSE_PROTOCOL "^HTTP\/0\.9" "phase:3,id:57,t:none"`

## RESPONSE_STATUS

This variable holds the HTTP response status code:

`SecRule RESPONSE_STATUS "^[45]" "phase:3,id:58,t:none"`

This variable may not work as expected in embedded mode, as Apache
sometimes handles certain requests differently, and without invoking
ModSecurity (all other modules).

## RULE

This is a special collection that provides access to the id, rev,
severity, logdata, and msg fields of the rule that triggered the action.
It can be used to refer to only the same rule in which it resides.

`SecRule &REQUEST_HEADERS:Host "@eq 0" "log,deny,id:59,setvar:tx.varname=%{RULE.id}"`

## SCRIPT_BASENAME

This variable holds just the local filename part of SCRIPT_FILENAME.

**Version:** 2.x

**Supported on libModSecurity:** TBI

`SecRule SCRIPT_BASENAME "^login\.php$" "id:60"`

Note : Not available in proxy mode.

## SCRIPT_FILENAME

This variable holds the full internal path to the script that will be
used to serve the request.

**Version:** 2.x

**Supported on libModSecurity:** TBI

`SecRule SCRIPT_FILENAME "^/usr/local/apache/cgi-bin/login\.php$" "id:61"`

Note : Not available in proxy mode.

## SCRIPT_GID

This variable holds the numerical identifier of the group owner of the
script.

**Version:** 2.x

**Supported on libModSecurity:** TBI

`SecRule SCRIPT_GID "!^46$" "id:62"`

Note : Not available in proxy mode.

## SCRIPT_GROUPNAME

This variable holds the name of the group owner of the script.

**Version:** 2.x

**Supported on libModSecurity:** TBI

`SecRule SCRIPT_GROUPNAME "!^apache$" "id:63"`

Note : Not available in proxy mode.

## SCRIPT_MODE

This variable holds the script's permissions mode data (e.g., 644).

**Version:** 2.x

**Supported on libModSecurity:** TBI

    # Do not allow scripts that can be written to
    SecRule SCRIPT_MODE "^(2|3|6|7)$" "id:64"

Note : Not available in proxy mode.

## SCRIPT_UID

This variable holds the numerical identifier of the owner of the script.

**Version:** 2.x

**Supported on libModSecurity:** TBI

    # Do not run any scripts that are owned 
    # by Apache (Apache's user id is 46) 
    SecRule SCRIPT_UID "!^46$" "id:65"

Note : Not available in proxy mode.

## SCRIPT_USERNAME

This variable holds the username of the owner of the script.

**Version:** 2.x

**Supported on libModSecurity:** TBI

    # Do not run any scripts owned by Apache SecRule 
    SCRIPT_USERNAME "^apache$" "id:66"

Note : Not available in proxy mode.

## SDBM_DELETE_ERROR

**Version:** 2.x

**Supported on libModSecurity:** No

This variable is set to 1 when APR fails to delete SDBM entries.

## SERVER_ADDR

This variable contains the IP address of the server.

`SecRule SERVER_ADDR "@ipMatch 192.168.1.100" "id:67"`

## SERVER_NAME

This variable contains the transaction's hostname or IP address, taken
from the request itself (which means that, in principle, it should not
be trusted).

`SecRule SERVER_NAME "hostname\.com$" "id:68"`

## SERVER_PORT

This variable contains the local port that the web server (or reverse
proxy) is listening on.

`SecRule SERVER_PORT "^80$" "id:69"`

## SESSION

This variable is a collection that contains session information. It
becomes available only after setsid is executed.

The following example shows how to initialize SESSION using setsid, how
to use setvar to increase the SESSION.score values, how to set the
SESSION.blocked variable, and finally, how to deny the connection based
on the <SESSION:blocked> value:

    # Initialize session storage 
    SecRule REQUEST_COOKIES:PHPSESSID !^$ "phase:2,id:70,nolog,pass,setsid:%{REQUEST_COOKIES.PHPSESSID}"

    # Increment session score on attack 
    SecRule REQUEST_URI "^/cgi-bin/finger$" "phase:2,id:71,t:none,t:lowercase,t:normalizePath,pass,setvar:SESSION.score=+10" 

    # Detect too many attacks in a session
    SecRule SESSION:score "@gt 50" "phase:2,id:72,pass,setvar:SESSION.blocked=1"

    # Enforce session block 
    SecRule SESSION:blocked "@eq 1" "phase:2,id:73,deny,status:403"

## SESSIONID

This variable contains the value set with setsid. See SESSION (above)
for a complete example.

## STATUS_LINE

This variable holds the full status line sent by the server (including
the request method and HTTP version information).

    # Generate an alert when the application generates 500 errors.
    SecRule STATUS_LINE "@contains 500" "phase:3,id:49,log,pass,logdata:'Application error detected!,t:none"

**Version:** 2.x

**Supported on libModSecurity:** TBI

## STREAM_INPUT_BODY

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** No

This variable give access to the raw request body content. This variable
is best used for two use-cases:

1.  For fast pattern matching - using \@pm/@pmf to prequalify large text
    strings against any kind of content-type data. This is more
    performant vs. using REQUEST_BODY/ARGS_POST/ARGS_POST_NAMES as it
    happens before ModSecurity parsing in phase:2 variable population.
2.  For data substitution - using \@rsub against this variable allows
    you to manipulate live request body data. Example - to remove
    offending payloads or to substitute benign data.

Note : You must enable the SecStreamInBodyInspection directive

```{=html}
<!-- -->
```

Note : This directive is NOT supported for libModSecurity (v3).

## STREAM_OUTPUT_BODY

This variable give access to the raw response body content. This
variable is best used for case:

1.  For data substitution - using \@rsub against this variable allows
    you to manipulate live request body data. Example - to remove
    offending payloads or to substitute benign data.

**Version:** 2.6.0-2.9.x

**Supported on libModSecurity:** TBD

Note : You must enable the SecStreamOutBodyInspection directive

## TIME

This variable holds a formatted string representing the time
(hour:minute:second).

`SecRule TIME "^(([1](8|9))|([2](0|1|2|3))):\d{2}:\d{2}$" "id:74"`

## TIME_DAY

This variable holds the current date (1--31). The following rule
triggers on a transaction that's happening anytime between the 10th and
20th in a month:

`SecRule TIME_DAY "^(([1](0|1|2|3|4|5|6|7|8|9))|20)$" "id:75"`

## TIME_EPOCH

This variable holds the time in seconds since 1970.

## TIME_HOUR

This variable holds the current hour value (0--23). The following rule
triggers when a request is made "off hours":

`SecRule TIME_HOUR "^(0|1|2|3|4|5|6|[1](8|9)|[2](0|1|2|3))$" "id:76"`

## TIME_MIN

This variable holds the current minute value (0--59). The following rule
triggers during the last half hour of every hour:

`SecRule TIME_MIN "^(3|4|5)" "id:77"`

## TIME_MON

This variable holds the current month value (0--11). The following rule
matches if the month is either November (value 10) or December (value
11):

`SecRule TIME_MON "^1" "id:78"`

## TIME_SEC

This variable holds the current second value (0--59).

`SecRule TIME_SEC "@gt 30" "id:79"`

## TIME_WDAY

This variable holds the current weekday value (0--6). The following rule
triggers only on Satur- day and Sunday:

`SecRule TIME_WDAY "^(0|6)$" "id:80"`

## TIME_YEAR

This variable holds the current four-digit year value.

`SecRule TIME_YEAR "^2006$" "id:81"`

## TX

This is the transient transaction collection, which is used to store
pieces of data, create a transaction anomaly score, and so on. The
variables placed into this collection are available only until the
transaction is complete.

    # Increment transaction attack score on attack 
    SecRule ARGS attack "phase:2,id:82,nolog,pass,setvar:TX.score=+5"

    # Block the transactions whose scores are too high 
    SecRule TX:SCORE "@gt 20" "phase:2,id:83,log,deny"

Some variable names in the TX collection are reserved and cannot be
used:

-   TX:0: the matching value when using the \@rx or \@pm operator with
    the capture action
-   TX:1-TX:9: the captured subexpression value when using the \@rx
    operator with capturing parens and the capture action
-   TX:MSC\_.\*: ModSecurity processing flags
-   MSC_PCRE_LIMITS_EXCEEDED: Set to nonzero if PCRE match limits are
    exceeded. See SecPcreMatchLimit and SecPcreMatchLimitRecursion for
    more information.

## UNIQUE_ID

This variable holds the data created by mod_unique_id
[8](http://httpd.apache.org/docs/2.2/mod/mod_unique_id.html). This
module provides a magic token for each request which is guaranteed to be
unique across \"all\" requests under very specific conditions. The
unique identifier is even unique across multiple machines in a properly
configured cluster of machines. The environment variable UNIQUE_ID is
set to the identifier for each request. The UNIQUE_ID environment
variable is constructed by encoding the 112-bit (32-bit IP address, 32
bit pid, 32 bit time stamp, 16 bit counter) quadruple using the alphabet
\[A-Za-z0-9@-\] in a manner similar to MIME base64 encoding, producing
19 characters.

## URLENCODED_ERROR

This variable is created when an invalid URL encoding is encountered
during the parsing of a query string (on every request) or during the
parsing of an application/x-www-form-urlencoded request body (only on
the requests that use the URLENCODED request body processor).

## USERID

This variable contains the value set with setuid.

    # Initialize user tracking
    SecAction "nolog,id:84,pass,setuid:%{REMOTE_USER}" 

    # Is the current user the administrator?
    SecRule USERID "admin" "id:85"

## USERAGENT_IP

This variable is created when running modsecurity with apache2.4 and
will contains the client ip address set by mod_remoteip in proxied
connections.

**Version:** 2.x

**Supported on libModSecurity:** TBI

## WEBAPPID

This variable contains the current application name, which is set in
configuration using SecWebAppId.

**Version:** 2.0.0-2.9.x

**Supported on libModSecurity:** TBI

## WEBSERVER_ERROR_LOG

**Version:** 2.x

**Supported on libModSecurity:** TBI

Contains zero or more error messages produced by the web server. This
variable is best accessed from phase 5 (logging).

`SecRule WEBSERVER_ERROR_LOG "File does not exist" "phase:5,id:86,t:none,nolog,pass,setvar:TX.score=+5"`

## XML

Special collection used to interact with the XML parser. It can be used
standalone as a target for the validateDTD and validateSchema operator.
Otherwise, it must contain a valid XPath expression, which will then be
evaluated against a previously parsed XML DOM tree.

    SecDefaultAction log,deny,status:403,phase:2,id:90
    SecRule REQUEST_HEADERS:Content-Type ^text/xml$ "phase:1,id:87,t:lowercase,nolog,pass,ctl:requestBodyProcessor=XML"
    SecRule REQBODY_PROCESSOR "!^XML$" skipAfter:12345,id:88

    SecRule XML:/employees/employee/name/text() Fred "id:89"
    SecRule XML:/xq:employees/employee/name/text() Fred "id:12345,xmlns:xq=http://www.example.com/employees"

The first XPath expression does not use namespaces. It would match
against payload such as this one:

    <employees>
        <employee>
            <name>Fred Jones</name>
            <address location="home">
                <street>900 Aurora Ave.</street>
                <city>Seattle</city>
                <state>WA</state>
                <zip>98115</zip>
            </address>
            <address location="work">
                <street>2011 152nd Avenue NE</street>
                <city>Redmond</city>
                <state>WA</state>
                <zip>98052</zip>
            </address>
            <phone location="work">(425)555-5665</phone>
            <phone location="home">(206)555-5555</phone>
            <phone location="mobile">(206)555-4321</phone>
        </employee>
    </employees>

The second XPath expression does use namespaces. It would match the
following payload:

    <xq:employees xmlns:xq="http://www.example.com/employees">
        <employee>
            <name>Fred Jones</name>
            <address location="home">
                <street>900 Aurora Ave.</street>
                <city>Seattle</city>
                <state>WA</state>
                <zip>98115</zip>
            </address>
            <address location="work">
                <street>2011 152nd Avenue NE</street>
                <city>Redmond</city>
                <state>WA</state>
                <zip>98052</zip>
            </address>
            <phone location="work">(425)555-5665</phone>
            <phone location="home">(206)555-5555</phone>
            <phone location="mobile">(206)555-4321</phone>
        </employee>
    </xq:employees>

Note the different namespace used in the second example.

# Transformation functions {#transformation_functions}

Transformation functions are used to alter input data before it is used
in matching (i.e., operator execution). The input data is never
modified, actually---whenever you request a transformation function to
be used, ModSecurity will create a copy of the data, transform it, and
then run the operator against the result.

Note : There are no default transformation functions, as there were in the first generation of ModSecurity (1.x).

In the following example, the request parameter values are converted to
lowercase before matching:

`SecRule ARGS "xp_cmdshell" "t:lowercase,id:91"`

Multiple transformation actions can be used in the same rule, forming a
transformation pipeline. The transformations will be performed in the
order in which they appear in the rule.

In most cases, the order in which transformations are performed is very
important. In the following example, a series of transformation
functions is performed to counter evasion. Performing the
transformations in any other order would allow a skillful attacker to
evade detection:

`SecRule ARGS "(asfunction|javascript|vbscript|data|mocha|livescript):" "id:92,t:none,t:htmlEntityDecode,t:lowercase,t:removeNulls,t:removeWhitespace"`

Warning : It is currently possible to use SecDefaultAction to specify a default list of transformation functions, which will be applied to all rules that follow the SecDefaultAction directive. However, this practice is not recommended, because it means that mistakes are very easy to make. It is recommended that you always specify the transformation functions that are needed by a particular rule, starting the list with t:none (which clears the possibly inherited transformation functions).

The remainder of this section documents the transformation functions
currently available in ModSecurity.

## base64Decode

Decodes a Base64-encoded string.

    SecRule REQUEST_HEADERS:Authorization "^Basic ([a-zA-Z0-9]+=*)$" "phase:1,id:93,capture,chain,logdata:%{TX.1}"
      SecRule TX:1 ^(\w+): t:base64Decode,capture,chain
        SecRule TX:1 ^(admin|root|backup)$ 

Note : Be careful when applying base64Decode with other transformations. The order of your transformation matters in this case as certain transformations may change or invalidate the base64 encoded string prior to being decoded (i.e t:lowercase, etc). This of course means that it is also very difficult to write a single rule that checks for a base64decoded value OR an unencoded value with transformations, it is best to write two rules in this situation.

## sqlHexDecode

Decode sql hex data. Example (0x414243) will be decoded to (ABC).
Available as of 2.6.3

## base64DecodeExt

Decodes a Base64-encoded string. Unlike base64Decode, this version uses
a forgiving implementation, which ignores invalid characters. Available
as of 2.5.13.

See blog post on Base64Decoding evasion issues on PHP sites -
<http://blog.spiderlabs.com/2010/04/impedance-mismatch-and-base64.html>

## base64Encode

Encodes input string using Base64 encoding.

## cmdLine

Note : This is a community contribution developed by Marc Stern [9](http://www.linkedin.com/in/marcstern)

In Windows and Unix, commands may be escaped by different means, such
as:

-   c\^ommand /c \...
-   \"command\" /c \...
-   command,/c \...
-   backslash in the middle of a Unix command

The cmdLine transformation function avoids this problem by manipulating
the variable contend in the following ways:

-   deleting all backslashes \[\\\]
-   deleting all double quotes \[\"\]
-   deleting all single quotes \[\'\]
-   deleting all carets \[\^\]
-   deleting spaces before a slash \[/\]
-   deleting spaces before an open parentesis \[(\]
-   replacing all commas \[,\] and semicolon \[;\] into a space
-   replacing all multiple spaces (including tab, newline, etc.) into
    one space
-   transform all characters to lowercase

**Example Usage:**

    SecRule ARGS "(?:command(?:.com)?|cmd(?:.exe)?)(?:/.*)?/[ck]" "phase:2,id:94,t:none, t:cmdLine"

## compressWhitespace

Converts any of the whitespace characters (0x20, \\f, \\t, \\n, \\r,
\\v, 0xa0) to spaces (ASCII 0x20), compressing multiple consecutive
space characters into one.

## cssDecode

Decodes characters encoded using the CSS 2.x escape rules
[syndata.html#characters](http://www.w3.org/TR/CSS2/). This function
uses only up to two bytes in the decoding process, meaning that it is
useful to uncover ASCII characters encoded using CSS encoding (that
wouldn't normally be encoded), or to counter evasion, which is a
combination of a backslash and non-hexadecimal characters (e.g.,
ja\\vascript is equivalent to javascript).

## escapeSeqDecode

Decodes ANSI C escape sequences: \\a, \\b, \\f, \\n, \\r, \\t, \\v,
\\\\, \\?, \\\', \\\", \\xHH (hexadecimal), \\0OOO (octal). Invalid
encodings are left in the output.

## hexDecode

Decodes a string that has been encoded using the same algorithm as the
one used in hexEncode (see following entry).

## hexEncode

Encodes string (possibly containing binary characters) by replacing each
input byte with two hexadecimal characters. For example, xyz is encoded
as 78797a.

## htmlEntityDecode

Decodes the characters encoded as HTML entities. The following variants
are supported:

-   &#xHH and &#xHH; (where H is any hexadecimal number)
-   &#DDD and &#DDD; (where D is any decimal number)
-   &quotand\"
-   &nbspand 
-   &ltand\<
-   &gtand\>

This function always converts one HTML entity into one byte, possibly
resulting in a loss of information (if the entity refers to a character
that cannot be represented with the single byte). It is thus useful to
uncover bytes that would otherwise not need to be encoded, but it cannot
do anything meaningful with the characters from the range above 0xff.

## jsDecode

Decodes JavaScript escape sequences. If a \\uHHHH code is in the range
of FF01-FF5E (the full width ASCII codes), then the higher byte is used
to detect and adjust the lower byte. Otherwise, only the lower byte will
be used and the higher byte zeroed (leading to possible loss of
information).

## length

Looks up the length of the input string in bytes, placing it (as string)
in output. For example, if it gets ABCDE on input, this transformation
function will return 5 on output.

## lowercase

Converts all characters to lowercase using the current C locale.

## md5

Calculates an MD5 hash from the data in input. The computed hash is in a
raw binary form and may need encoded into text to be printed (or
logged). Hash functions are commonly used in combination with hexEncode
(for example: t:md5,t:hexEncode).

## none

Not an actual transformation function, but an instruction to ModSecurity
to remove all transformation functions associated with the current rule.

## normalisePath

See normalizePath.

## normalizePath

Removes multiple slashes, directory self-references, and directory
back-references (except when at the beginning of the input) from input
string.

Note : As of 2010 normalisePath has been renamed to normalizePath (MODSEC-103). NormalisePath is kept for backwards compatibility in current versions, but should not be used.

## normalisePathWin

See normalizePathWin.

## normalizePathWin

Same as normalizePath, but first converts backslash characters to
forward slashes.

Note : As of 2010 normalisePathWin has been renamed to normalizePathWin (MODSEC-103). NormalisePathWin is kept for backwards compatibility in current versions, but should not be used.

## parityEven7bit

Calculates even parity of 7-bit data replacing the 8th bit of each
target byte with the calculated parity bit.

## parityOdd7bit

Calculates odd parity of 7-bit data replacing the 8th bit of each target
byte with the calculated parity bit.

## parityZero7bit

Calculates zero parity of 7-bit data replacing the 8th bit of each
target byte with a zero-parity bit, which allows inspection of even/odd
parity 7-bit data as ASCII7 data.

## removeNulls

Removes all NUL bytes from input.

## removeWhitespace

Removes all whitespace characters from input.

## replaceComments

Replaces each occurrence of a C-style comment (/\* \... \*/) with a
single space (multiple consecutive occurrences of which will not be
compressed). Unterminated comments will also be replaced with a space
(ASCII 0x20). However, a standalone termination of a comment (\*/) will
not be acted upon.

## removeCommentsChar

Removes common comments chars (/\*, \*/, \--, #).

## removeComments

**Version:** 2.x-3.x

**Supported on libModSecurity:** Yes

Removes each occurrence of comment (/\* \... \*/, \--, #). Multiple
consecutive occurrences of which will not be compressed.

Note : **This transformation is known to be unreliable, might cause some unexpected behaviour and could be deprecated soon in a future release. Refer to issue [#1207](https://github.com/SpiderLabs/ModSecurity/issues/1207) for further information.**.

## replaceNulls

Replaces NUL bytes in input with space characters (ASCII 0x20).

## urlDecode

Decodes a URL-encoded input string. Invalid encodings (i.e., the ones
that use non-hexadecimal characters, or the ones that are at the end of
string and have one or two bytes missing) are not converted, but no
error is raised. To detect invalid encodings, use the
\@validateUrlEncoding operator on the input data first. The
transformation function should not be used against variables that have
already been URL-decoded (such as request parameters) unless it is your
intention to perform URL decoding twice!

## uppercase

Converts all characters to uppercase using the current C locale.

**Version:** 3.x

**Supported on libModSecurity:** Yes

## urlDecodeUni

Like urlDecode, but with support for the Microsoft-specific %u encoding.
If the code is in the range of FF01-FF5E (the full-width ASCII codes),
then the higher byte is used to detect and adjust the lower byte.
Otherwise, only the lower byte will be used and the higher byte zeroed.

## urlEncode

Encodes input string using URL encoding.

## utf8toUnicode

Converts all UTF-8 character sequences to Unicode (using \'%uHHHH\'
format). This help input normalization specially for non-english
languages minimizing false-positives and false-negatives.

## sha1

Calculates a SHA1 hash from the input string. The computed hash is in a
raw binary form and may need encoded into text to be printed (or
logged). Hash functions are commonly used in combination with hexEncode
(for example, t:sha1,t:hexEncode).

## trimLeft

Removes whitespace from the left side of the input string.

## trimRight

Removes whitespace from the right side of the input string.

## trim

Removes whitespace from both the left and right sides of the input
string.

# Actions

Each action belongs to one of five groups:

-   **Disruptive actions** - Cause ModSecurity to do something. In many
    cases something means block transaction, but not in all. For
    example, the allow action is classified as a disruptive action, but
    it does the opposite of blocking. There can only be one disruptive
    action per rule (if there are multiple disruptive actions present,
    or inherited, only the last one will take effect), or rule chain (in
    a chain, a disruptive action can only appear in the first rule).

Note : **Disruptive actions will NOT be executed if the SecRuleEngine is set to DetectionOnly**. If you are creating exception/whitelisting rules that use the allow action, you should also add the ctl:ruleEngine=On action to execute the action.

-   **Non-disruptive action**s - Do something, but that something does
    not and cannot affect the rule processing flow. Setting a variable,
    or changing its value is an example of a non-disruptive action.
    Non-disruptive action can appear in any rule, including each rule
    belonging to a chain.
-   **Flow actions** - These actions affect the rule flow (for example
    skip or skipAfter).
-   **Meta-data actions** - Meta-data actions are used to provide more
    information about rules. Examples include id, rev, severity and msg.
-   **Data actions** - Not really actions, these are mere containers
    that hold data used by other actions. For example, the status action
    holds the status that will be used for blocking (if it takes place).

## accuracy

**Description:** Specifies the relative accuracy level of the rule
related to false positives/negatives. The value is a string based on a
numeric scale (1-9 where 9 is very strong and 1 has many false
positives).

**Action Group:** Meta-data

**Version:** 2.7

**Example:**

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/* "\bgetparentfolder\b" \
        "phase:2,ver:'CRS/2.2.4,accuracy:'9',maturity:'9',capture,t:none,t:htmlEntityDecode,t:compressWhiteSpace,t:lowercase,ctl:auditLogParts=+E,block,msg:'Cross-site Scripting (XSS) Attack',id:'958016',tag:'WEB_ATTACK/XSS',tag:'WASCTC/WASC-8',tag:'WASCTC/WASC-22',tag:'OWASP_TOP_10/A2',tag:'OWASP_AppSensor/IE1',tag:'PCI/6.5.1',logdata:'% \
    {TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.xss_score=+%{tx.critical_anomaly_score},setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/XSS-%{matched_var_name}=%{tx.0}"

## allow

**Description:** Stops rule processing on a successful match and allows
the transaction to proceed.

**Action Group:** Disruptive

Example:

    # Allow unrestricted access from 192.168.1.100 
    SecRule REMOTE_ADDR "^192\.168\.1\.100$" phase:1,id:95,nolog,allow

Prior to ModSecurity 2.5 the allow action would only affect the current
phase. An allow in phase 1 would skip processing the remaining rules in
phase 1 but the rules from phase 2 would execute. Starting with v2.5.0
allow was enhanced to allow for fine-grained control of what is done.
The following rules now apply:

1.  If used one its own, like in the example above, allow will affect
    the entire transaction, stopping processing of the current phase but
    also skipping over all other phases apart from the logging phase.
    (The logging phase is special; it is designed to always execute.)
2.  If used with parameter \"phase\", allow will cause the engine to
    stop processing the current phase. Other phases will continue as
    normal.
3.  If used with parameter \"request\", allow will cause the engine to
    stop processing the current phase. The next phase to be processed
    will be phase RESPONSE_HEADERS.

Examples:

    # Do not process request but process response.
    SecAction phase:1,allow:request,id:96

    # Do not process transaction (request and response).
    SecAction phase:1,allow,id:97

If you want to allow a response through, put a rule in phase
RESPONSE_HEADERS and simply use allow on its own:

    # Allow response through.
    SecAction phase:3,allow,id:98

## append

**Description**: Appends text given as parameter to the end of response
body. Content injection must be en- abled (using the SecContentInjection
directive). No content type checks are made, which means that before
using any of the content injection actions, you must check whether the
content type of the response is adequate for injection.

**Version:** 2.x-2.9.x

**Supported on libModSecurity:** No

**Action Group:** Non-disruptive

**Processing Phases:** 3 and 4.

Example:

    SecRule RESPONSE_CONTENT_TYPE "^text/html" "nolog,id:99,pass,append:'<hr>Footer'"

Warning : Although macro expansion is allowed in the additional content, you are strongly cau- tioned against inserting user-defined data fields into output. Doing so would create a cross-site scripting vulnerability.

## auditlog

**Description:** Marks the transaction for logging in the audit log.

**Action Group**: Non-disruptive

Example:

`SecRule REMOTE_ADDR "^192\.168\.1\.100$" auditlog,phase:1,id:100,allow`

Note : The auditlog action is now explicit if log is already specified.

## block

**Description:** Performs the disruptive action defined by the previous
SecDefaultAction.

**Action Group:** Disruptive

This action is essentially a placeholder that is intended to be used by
rule writers to request a blocking action, but without specifying how
the blocking is to be done. The idea is that such decisions are best
left to rule users, as well as to allow users, to override blocking if
they so desire. In future versions of ModSecurity, more control and
functionality will be added to define \"how\" to block.

Examples:

    # Specify how blocking is to be done 
    SecDefaultAction phase:2,deny,id:101,status:403,log,auditlog

    # Detect attacks where we want to block 
    SecRule ARGS attack1 phase:2,block,id:102

    # Detect attacks where we want only to warn 
    SecRule ARGS attack2 phase:2,pass,id:103

It is possible to use the SecRuleUpdateActionById directive to override
how a rule handles blocking. This is useful in three cases:

1.  If a rule has blocking hard-coded, and you want it to use the policy
    you determine
2.  If a rule was written to block, but you want it to only warn
3.  If a rule was written to only warn, but you want it to block

The following example demonstrates the first case, in which the
hard-coded block is removed in favor of the user-controllable block:

    # Specify how blocking is to be done 
    SecDefaultAction phase:2,deny,status:403,log,auditlog,id:104

    # Detect attacks and block 
    SecRule ARGS attack1 phase:2,id:1,deny

    # Change how rule ID 1 blocks 
    SecRuleUpdateActionById 1 block

## capture

**Description:** When used together with the regular expression operator
(@rx), the capture action will create copies of the regular expression
captures and place them into the transaction variable collection.

**Action Group:** Non-disruptive

Example:

    SecRule REQUEST_BODY "^username=(\w{25,})" phase:2,capture,t:none,chain,id:105
      SecRule TX:1 "(?:(?:a(dmin|nonymous)))"

Up to 10 captures will be copied on a successful pattern match, each
with a name consisting of a digit from 0 to 9. The TX.0 variable always
contains the entire area that the regular expression matched. All the
other variables contain the captured values, in the order in which the
capturing parentheses appear in the regular expression.

## chain

**Description:** Chains the current rule with the rule that immediately
follows it, creating a rule chain. Chained rules allow for more complex
processing logic.

**Action Group:** Flow

Example:

    # Refuse to accept POST requests that do not contain Content-Length header. 
    # (Do note that this rule should be preceded by a rule 
    # that verifies only valid request methods are used.) 
    SecRule REQUEST_METHOD "^POST$" phase:1,chain,t:none,id:105
      SecRule &REQUEST_HEADERS:Content-Length "@eq 0" t:none

Note : Rule chains allow you to simulate logical AND. The disruptive actions specified in the first portion of the chained rule will be triggered only if all of the variable checks return positive hits. If any one aspect of a chained rule comes back negative, then the entire rule chain will fail to match. Also note that disruptive actions, execution phases, metadata actions (id, rev, msg, tag, severity, logdata), skip, and skipAfter actions can be specified only by the chain starter rule.

The following directives can be used in rule chains:

-   SecAction
-   SecRule
-   SecRuleScript

Special rules control the usage of actions in chained rules:

-   Any actions that affect the rule flow (i.e., the disruptive actions,
    skip and skipAfter) can be used only in the chain starter. They will
    be executed only if the entire chain matches.
-   Non-disruptive actions can be used in any rule; they will be
    executed if the rule that contains them matches and not only when
    the entire chain matches.
-   The metadata actions (e.g., id, rev, msg) can be used only in the
    chain starter.

## ctl

**Description**: Changes ModSecurity configuration on transient,
per-transaction basis. Any changes made using this action will affect
only the transaction in which the action is executed. The default
configuration, as well as the other transactions running in parallel,
will be unaffected.

**Action Group:** Non-disruptive

**Example:**

    # Parse requests with Content-Type "text/xml" as XML 
    SecRule REQUEST_CONTENT_TYPE ^text/xml "nolog,pass,id:106,ctl:requestBodyProcessor=XML"

    # white-list the user parameter for rule #981260 when the REQUEST_URI is /index.php
    SecRule REQUEST_URI "@beginsWith /index.php" "phase:1,t:none,pass, \
      nolog,ctl:ruleRemoveTargetById=981260;ARGS:user

The following configuration options are supported:

1.  **auditEngine**
2.  **auditLogParts**
3.  **debugLogLevel** (Supported on libModSecurity: TBI)
4.  **forceRequestBodyVariable**
5.  **requestBodyAccess**
6.  **requestBodyLimit** (Supported on libModSecurity: TBI)
7.  **requestBodyProcessor**
8.  **responseBodyAccess** (Supported on libModSecurity: TBI)
9.  **responseBodyLimit** (Supported on libModSecurity: TBI)
10. **ruleEngine**
11. **ruleRemoveById** - since this action us triggered at run time, it
    should be specified **before** the rule in which it is disabling.
12. **ruleRemoveByMsg** (Supported on libModSecurity: TBI)
13. **ruleRemoveByTag** (Supported on libModSecurity: TBI)
14. **ruleRemoveTargetById** - since this action is used to just remove
    targets, users don\'t need to use the char ! before the target list.
15. **ruleRemoveTargetByMsg** - since this action is used to just remove
    targets, users don\'t need to use the char ! before the target list.
    (Supported on libModSecurity: TBI)
16. **ruleRemoveTargetByTag** - since this action is used to just remove
    targets, users don\'t need to use the char ! before the target list.
17. **hashEngine** (Supported on libModSecurity: TBI)
18. **hashEnforcement** (Supported on libModSecurity: TBI)

With the exception of the requestBodyProcessor and
forceRequestBodyVariable settings, each configuration option corresponds
to one configuration directive and the usage is identical.

The requestBodyProcessor option allows you to configure the request body
processor. By default, ModSecurity will use the URLENCODED and MULTIPART
processors to process an application/x-www-form-urlencoded and a
multipart/form-data body, respectively. Other two processors are also
supported: JSON and XML, but they are never used implicitly. Instead,
you must tell ModSecurity to use it by placing a few rules in the
REQUEST_HEADERS processing phase. After the request body is processed as
XML, you will be able to use the XML-related features to inspect it.

Request body processors will not interrupt a transaction if an error
occurs during parsing. Instead, they will set the variables
REQBODY_PROCESSOR_ERROR and REQBODY_PROCESSOR_ERROR_MSG. These variables
should be inspected in the REQUEST_BODY phase and an appropriate action
taken. The forceRequestBodyVariable option allows you to configure the
REQUEST_BODY variable to be set when there is no request body processor
configured. This allows for inspection of request bodies of unknown
types.

Note : There was a ctl:ruleUpdateTargetById introduced in 2.6.0 and removed from the code in 2.7.0. JSON was added as part of v2.8.0-rc1

## deny

**Description:** Stops rule processing and intercepts transaction.

**Action Group:** Disruptive

Example:
`SecRule REQUEST_HEADERS:User-Agent "nikto" "log,deny,id:107,msg:'Nikto Scanners Identified'"`

## deprecatevar

**Description**: Decrements numerical value over time, which makes sense
only applied to the variables stored in persistent storage.

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Action Group:** Non-Disruptive

Example: The following example will decrement the counter by 60 every
300 seconds.

    SecAction phase:5,id:108,nolog,pass,deprecatevar:SESSION.score=60/300

Counter values are always positive, meaning that the value will never go
below zero. Unlike expirevar, the deprecate action must be executed on
every request.

## drop

**Description:** Initiates an immediate close of the TCP connection by
sending a FIN packet.

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Action Group:** Disruptive

**Example:** The following example initiates an IP collection for
tracking Basic Authentication attempts. If the client goes over the
threshold of more than 25 attempts in 2 minutes, it will DROP subsequent
connections.

    SecAction phase:1,id:109,initcol:ip=%{REMOTE_ADDR},nolog
    SecRule ARGS:login "!^$" "nolog,phase:1,id:110,setvar:ip.auth_attempt=+1,deprecatevar:ip.auth_attempt=25/120"
    SecRule IP:AUTH_ATTEMPT "@gt 25" "log,drop,phase:1,id:111,msg:'Possible Brute Force Attack'"

Note : This action is currently not available on Windows based builds.

This action is extremely useful when responding to both Brute Force and
Denial of Service attacks in that, in both cases, you want to minimize
both the network bandwidth and the data returned to the client. This
action causes error message to appear in the log \"(9)Bad file
descriptor: core_output_filter: writing data to the network\"

## exec

**Description:** Executes an external script/binary supplied as
parameter. As of v2.5.0, if the parameter supplied to exec is a Lua
script (detected by the .lua extension) the script will be processed
internally. This means you will get direct access to the internal
request context from the script. Please read the SecRuleScript
documentation for more details on how to write Lua scripts.

**Action Group:** Non-disruptive

**Version:** 2.x

**Supported on libModSecurity:** YES

**Example:**

    # Run external program on rule match 
    SecRule REQUEST_URI "^/cgi-bin/script\.pl" "phase:2,id:112,t:none,t:lowercase,t:normalizePath,block,\ exec:/usr/local/apache/bin/test.sh"

    # Run Lua script on rule match 
    SecRule ARGS:p attack "phase:2,id:113,block,exec:/usr/local/apache/conf/exec.lua"

The exec action is executed independently from any disruptive actions
specified. External scripts will always be called with no parameters.
Some transaction information will be placed in environment variables.
All the usual CGI environment variables will be there. You should be
aware that forking a threaded process results in all threads being
replicated in the new process. Forking can therefore incur larger
overhead in a multithreaded deployment. The script you execute must
write something (anything) to stdout; if it doesn't, ModSecurity will
assume that the script failed, and will record the failure.

## expirevar

**Description:** Configures a collection variable to expire after the
given time period (in seconds).

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Action Group:** Non-disruptive

**Example:**

    SecRule REQUEST_COOKIES:JSESSIONID "!^$" "nolog,phase:1,id:114,pass,setsid:%{REQUEST_COOKIES:JSESSIONID}"
    SecRule REQUEST_URI "^/cgi-bin/script\.pl" "phase:2,id:115,t:none,t:lowercase,t:normalizePath,log,allow,setvar:session.suspicious=1,expirevar:session.suspicious=3600,phase:1"

You should use the expirevar actions at the same time that you use
setvar actions in order to keep the intended expiration time. If they
are used on their own (perhaps in a SecAction directive), the expire
time will be reset.

## id

**Description**: Assigns a unique ID to the rule or chain in which it
appears. Starting with ModSecurity 2.7 this action is mandatory and must
be numeric.

**Action Group:** Meta-data

**Example:**

    SecRule &REQUEST_HEADERS:Host "@eq 0" "log,id:60008,severity:2,msg:'Request Missing a Host Header'"

Note : The id action is required for all SecRule/SecAction directives as of v2.7.0

These are the reserved ranges:

-   1--99,999: reserved for local (internal) use. Use as you see fit,
    but do not use this range for rules that are distributed to others
-   100,000--199,999: reserved for rules published by Oracle
-   200,000--299,999: reserved for rules published Comodo
-   300,000--399,999: reserved for rules published at gotroot.com
-   400,000--419,999: unused (available for reservation)
-   420,000--429,999: reserved for ScallyWhack
    [10](http://projects.otaku42.de/wiki/Scally-Whack)
-   430,000--439,999: reserved for rules published by Flameeyes
    [11](http://www.flameeyes.eu/projects/modsec)
-   440.000-599,999: unused (available for reservation)
-   600,000-699,999: reserved for use by Akamai
    [12](http://www.akamai.com/html/solutions/waf.html)
-   700,000--799,999: reserved for Ivan Ristic
-   900,000--999,999: reserved for the OWASP ModSecurity Core Rule Set
    [13](http://www.owasp.org/index.php/Category:OWASP_ModSecurity_Core_Rule_Set_Project)
    project
-   1,000,000-1,009,999: reserved for rules published by Redhat Security
    Team
-   1,010,000-1,999,999: reserved for WAF \| Web Application Firewall
    and Load Balancer Security (kemptechnologies.com)
    [14](https://kemptechnologies.com/solutions/waf/)
-   2,000,000-2,999,999: reserved for rules from Trustwave\'s SpiderLabs
    Research team
-   3,000,000-3,999,999: reserved for use by Akamai
    [15](http://www.akamai.com/html/solutions/waf.html)
-   4,000,000-4,099,999 reserved: in use by AviNetworks
    [16](https://kb.avinetworks.com/docs/latest/vantage-web-app-firewall-beta/)
-   4,100,000-4,199,999 reserved: in use by Fastly
    [17](https://www.fastly.com/products/cloud-security/#products-cloud-security-web-application-firewall)
-   4,200,000-4,299,999 reserved: in use by CMS-Garden
    [18](https://www.cms-garden.org/en)
-   4,300,000-4,300,999 reserved: in use by Ensim.hu
    [19](http://ensim.hu/)
-   4,301,000-19,999,999: unused (available for reservation)
-   8,000,000-8,999,999 reserved: in use by Yandex
-   20,000,000-21,999,999: reserved for rules from Trustwave\'s
    SpiderLabs Research team
-   22,000,000-69,999,999: unused (available for reservation)
-   77,000,000-77,999,999 - reserved: in use by Imunify360 - production
    rules
-   88,000,000-88,999,999 - reserved: in use by Imunify360 - beta users
-   99,000,000-99,099,999 reserved for use by Microsoft
    <https://azure.microsoft.com/en-us/services/web-application-firewall/>
-   99,100,000-99,199,999 reserved for use by WPScan/Jetpack
-   99,200,000-99,209,999 reserved for use by SKUDONET
    [20](https://www.skudonet.com)

## initcol

**Description:** Initializes a named persistent collection, either by
loading data from storage or by creating a new collection in memory.

**Action Group:** Non-disruptive

**Example:** The following example initiates IP address tracking, which
is best done in phase 1:

    SecAction phase:1,id:116,nolog,pass,initcol:ip=%{REMOTE_ADDR}

Collections are loaded into memory on-demand, when the initcol action is
executed. A collection will be persisted only if a change was made to it
in the course of transaction processing.

See the \"Persistent Storage\" section for further details.

## log

**Description:** Indicates that a successful match of the rule needs to
be logged.

**Action Group:** Non-disruptive

**Example:**

    SecAction phase:1,id:117,pass,initcol:ip=%{REMOTE_ADDR},log

This action will log matches to the Apache error log file and the
ModSecurity audit log.

## logdata

**Description:** Logs a data fragment as part of the alert message.

**Action Group:** Non-disruptive

**Example:**

    SecRule ARGS:p "@rx <script>" "phase:2,id:118,log,pass,logdata:%{MATCHED_VAR}"

The logdata information appears in the error and/or audit log files.
Macro expansion is performed, so you may use variable names such as
%{TX.0} or %{MATCHED_VAR}. The information is properly escaped for use
with logging of binary data.

## maturity

**Description:** Specifies the relative maturity level of the rule
related to the length of time a rule has been public and the amount of
testing it has received. The value is a string based on a numeric scale
(1-9 where 9 is extensively tested and 1 is a brand new experimental
rule).

**Action Group:** Meta-data

**Version:** 2.7

**Example:**

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/* "\bgetparentfolder\b" \
        "phase:2,ver:'CRS/2.2.4,accuracy:'9',maturity:'9',capture,t:none,t:htmlEntityDecode,t:compressWhiteSpace,t:lowercase,ctl:auditLogParts=+E,block,msg:'Cross-site Scripting (XSS) Attack',id:'958016',tag:'WEB_ATTACK/XSS',tag:'WASCTC/WASC-8',tag:'WASCTC/WASC-22',tag:'OWASP_TOP_10/A2',tag:'OWASP_AppSensor/IE1',tag:'PCI/6.5.1',logdata:'% \
    {TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.xss_score=+%{tx.critical_anomaly_score},setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/XSS-%{matched_var_name}=%{tx.0}"

## msg

**Description:** Assigns a custom message to the rule or chain in which
it appears. The message will be logged along with every alert.

**Action Group:** Meta-data

**Example:**

    SecRule &REQUEST_HEADERS:Host "@eq 0" "log,id:60008,severity:2,msg:'Request Missing a Host Header'"

Note : The msg information appears in the error and/or audit log files and is not sent back to the client in response headers.

## multiMatch

**Description:** If enabled, ModSecurity will perform multiple operator
invocations for every target, before and after every anti-evasion
transformation is performed.

**Action Group:** Non-disruptive

**Example:**

    SecRule ARGS "attack" "phase1,log,deny,id:119,t:removeNulls,t:lowercase,multiMatch"

Normally, variables are inspected only once per rule, and only after all
transformation functions have been completed. With multiMatch, variables
are checked against the operator before and after every transformation
function that changes the input.

## noauditlog

**Description:** Indicates that a successful match of the rule should
not be used as criteria to determine whether the transaction should be
logged to the audit log.

**Action Group:** Non-disruptive

**Example:**

    SecRule REQUEST_HEADERS:User-Agent "Test" allow,noauditlog,id:120

If the SecAuditEngine is set to On, all of the transactions will be
logged. If it is set to RelevantOnly, then you can control the logging
with the noauditlog action.

The noauditlog action affects only the current rule. If you prevent
audit logging in one rule only, a match in another rule will still cause
audit logging to take place. If you want to prevent audit logging from
taking place, regardless of whether any rule matches, use
ctl:auditEngine=Off.

## nolog

**Description:** Prevents rule matches from appearing in both the error
and audit logs.

**Action Group:** Non-disruptive

**Example:**

    SecRule REQUEST_HEADERS:User-Agent "Test" allow,nolog,id:121

Although nolog implies noauditlog, you can override the former by using
nolog,auditlog.

## pass

**Description:** Continues processing with the next rule in spite of a
successful match.

**Action Group:** Disruptive

**Example:**

    SecRule REQUEST_HEADERS:User-Agent "Test" "log,pass,id:122"

When using pass with a SecRule with multiple targets, all variables will
be inspected and all non-disruptive actions trigger for every match. In
the following example, the TX.test variable will be incremented once for
every request parameter:

    # Set TX.test to zero 
    SecAction "phase:2,nolog,pass,setvar:TX.test=0,id:123"

    # Increment TX.test for every request parameter 
    SecRule ARGS "test" "phase:2,log,pass,setvar:TX.test=+1,id:124"

## pause

**Description:** Pauses transaction processing for the specified number
of milliseconds. Starting with ModSecurity 2.7 this feature also
supports macro expansion.

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Action Group:** Disruptive

**Example:**

    SecRule REQUEST_HEADERS:User-Agent "Test" "log,pause:5000,id:125"

Warning : This feature can be of limited benefit for slowing down brute force authentication attacks, but use with care. If you are under a denial of service attack, the pause feature may make matters worse, as it will cause an entire Apache worker (process or thread, depending on the deployment mode) to sit idle until the pause is completed.

## phase

**Description**: Places the rule or chain into one of five available
processing phases. It can also be used in SecDefaultAction to establish
the rule defaults for that phase.

**Action Group:** Meta-data

**Example:**

    # Initialize IP address tracking in phase 1
    SecAction phase:1,nolog,pass,id:126,initcol:IP=%{REMOTE_ADDR}

Starting in ModSecurity version v2.7 there are aliases for some phase
numbers:

-   **2 - request**
-   **4 - response**
-   **5 - logging**

**Example:**

    SecRule REQUEST_HEADERS:User-Agent "Test" "phase:request,log,deny,id:127"

Warning : Keep in mind that if you specify the incorrect phase, the variable used in the rule may not yet be available. This could lead to a false negative situation where your variable and operator may be correct, but it misses malicious data because you specified the wrong phase.

## prepend

**Description:** Prepends the text given as parameter to response body.
Content injection must be enabled (using the SecContentInjection
directive). No content type checks are made, which means that before
using any of the content injection actions, you must check whether the
content type of the response is adequate for injection.

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Action Group:** Non-disruptive

**Processing Phases:** 3 and 4.

**Example:**

    SecRule RESPONSE_CONTENT_TYPE ^text/html \ "phase:3,nolog,pass,id:128,prepend:'Header<br>'"

Warning : Although macro expansion is allowed in the injected content, you are strongly cautioned against inserting user defined data fields int output. Doing so would create a cross-site scripting vulnerability.

## proxy

**Description:** Intercepts the current transaction by forwarding the
request to another web server using the proxy backend. The forwarding is
carried out transparently to the HTTP client (i.e., there's no external
redirection taking place).

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Action Group:** Disruptive

**Example:**

    SecRule REQUEST_HEADERS:User-Agent "Test" log,id:129,proxy:http://honeypothost/
    SecRule REQUEST_URI "@streq /test.txt" "phase:1,proxy:'[nocanon]http://$ENV{SERVER_NAME}:$ENV{SERVER_PORT}/test.txt',id:500005"

For this action to work, mod_proxy must also be installed. This action
is useful if you would like to proxy matching requests onto a honeypot
web server, and especially in combination with IP address or session
tracking.

Note: As of v2.9.1 the proxy action can receive a special parameter named \"\[nocanon\]\". The \"\[nocanon\]\" parameter will make the url to be delivered to the backend on its original format (raw). Further information about \"nocanon\" is available here: <https://httpd.apache.org/docs/2.2/pt-br/mod/mod_proxy.html>.

## redirect

**Description:** Intercepts transaction by issuing an external
(client-visible) redirection to the given location..

**Action Group:** Disruptive

**Example:**

    SecRule REQUEST_HEADERS:User-Agent "Test" "phase:1,id:130,log,redirect:http://www.example.com/failed.html"

If the status action is present on the same rule, and its value can be
used for a redirection (i.e., is one of the following: 301, 302, 303, or
307), the value will be used for the redirection status code. Otherwise,
status code 302 will be used.

## rev

**Description:** Specifies rule revision. It is useful in combination
with the id action to provide an indication that a rule has been
changed.

**Action Group:** Meta-data

**Example:**

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/* "(?:(?:[\;\|\`]\W*?\bcc|\b(wget|curl))\b|\/cc(?:[\'\"\|\;\`\-\s]|$))" \
                        "phase:2,rev:'2.1.3',capture,t:none,t:normalizePath,t:lowercase,ctl:auditLogParts=+E,block,msg:'System Command Injection',id:'950907',tag:'WEB_ATTACK/COMMAND_INJECTION',tag:'WASCTC/WASC-31',tag:'OWASP_TOP_10/A1',tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.command_injection_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/COMMAND_INJECTION-%{matched_var_name}=%{tx.0},skipAfter:END_COMMAND_INJECTION1"

Note : This action is used in combination with the id action to allow the same rule ID to be used after changes take place but to still provide some indication the rule changed.

## sanitiseArg

**Description:** Prevents sensitive request parameter data from being
logged to audit log. Each byte of the named parameter(s) is replaced
with an asterisk.

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Action Group:** Non-disruptive

**Example:**

    # Never log passwords 
    SecAction "nolog,phase:2,id:131,sanitiseArg:password,sanitiseArg:newPassword,sanitiseArg:oldPassword"

Note : The sanitize actions affect only the data as it is logged to audit log. High-level debug logs may contain sensitive data. Apache access log may contain sensitive data placed in the request URI.

## sanitiseMatched

**Description:** Prevents the matched variable (request argument,
request header, or response header) from being logged to audit log. Each
byte of the named parameter(s) is replaced with an asterisk.

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Action Group:** Non-disruptive

**Example:** This action can be used to sanitise arbitrary transaction
elements when they match a condition. For example, the example below
will sanitise any argument that contains the word password in the name.

    SecRule ARGS_NAMES password nolog,pass,id:132,sanitiseMatched

Note : The sanitize actions affect only the data as it is logged to audit log. High-level debug logs may contain sensitive data. Apache access log may contain sensitive data placed in the request URI.

## sanitiseMatchedBytes

**Description:** Prevents the matched string in a variable from being
logged to audit log. Each or a range of bytes of the named parameter(s)
is replaced with an asterisk.

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Action Group:** Non-disruptive

**Example:** This action can be used to sanitise arbitrary transaction
elements when they match a condition. For example, the example below
will sanitise the credit card number.

-   sanitiseMatchedBytes \-- This would x out only the bytes that
    matched.
-   sanitiseMatchedBytes:1/4 \-- This would x out the bytes that
    matched, but keep the first byte and last 4 bytes

```{=html}
<!-- -->
```
    # Detect credit card numbers in parameters and 
    # prevent them from being logged to audit log 
    SecRule ARGS "@verifyCC \d{13,16}" "phase:2,id:133,nolog,capture,pass,msg:'Potential credit card number in request',sanitiseMatchedBytes"
    SecRule RESPONSE_BODY "@verifyCC \d{13,16}" "phase:4,id:134,t:none,log,capture,block,msg:'Potential credit card number is response body',sanitiseMatchedBytes:0/4"

Note : The sanitize actions affect only the data as it is logged to audit log. High-level debug logs may contain sensitive data. Apache access log may contain sensitive data placed in the request URI. You must use capture action with sanitiseMatchedBytes, so the operator must support capture action. ie: \@rx, \@verifyCC.

## sanitiseRequestHeader

**Description:** Prevents a named request header from being logged to
audit log. Each byte of the named request header is replaced with an
asterisk..

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Action Group:** Non-disruptive

**Example:** This will sanitise the data in the Authorization header.

    SecAction "phase:1,nolog,pass,id:135,sanitiseRequestHeader:Authorization"

Note : The sanitize actions affect only the data as it is logged to audit log. High-level debug logs may contain sensitive data. Apache access log may contain sensitive data placed in the request URI.

## sanitiseResponseHeader

**Description:** Prevents a named response header from being logged to
audit log. Each byte of the named response header is replaced with an
asterisk.

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Action Group:** Non-disruptive

**Example:** This will sanitise the Set-Cookie data sent to the client.

    SecAction "phase:3,nolog,pass,id:136,sanitiseResponseHeader:Set-Cookie"

Note : The sanitize actions affect only the data as it is logged to audit log. High-level debug logs may contain sensitive data. Apache access log may contain sensitive data placed in the request URI.

## severity

**Description:** Assigns severity to the rule in which it is used.

**Action Group:** Meta-data

**Example:**

    SecRule REQUEST_METHOD "^PUT$" "id:340002,rev:1,severity:CRITICAL,msg:'Restricted HTTP function'"

Severity values in ModSecurity follows the numeric scale of syslog
(where 0 is the most severe). The data below is used by the OWASP
ModSecurity Core Rule Set (CRS):

-   **0 - EMERGENCY**: is generated from correlation of anomaly scoring
    data where there is an inbound attack and an outbound leakage.
-   **1 - ALERT**: is generated from correlation where there is an
    inbound attack and an outbound application level error.
-   **2 - CRITICAL**: Anomaly Score of 5. Is the highest severity level
    possible without correlation. It is normally generated by the web
    attack rules (40 level files).
-   **3 - ERROR**: Error - Anomaly Score of 4. Is generated mostly from
    outbound leakage rules (50 level files).
-   **4 - WARNING**: Anomaly Score of 3. Is generated by malicious
    client rules (35 level files).
-   **5 - NOTICE**: Anomaly Score of 2. Is generated by the Protocol
    policy and anomaly files.
-   **6 - INFO**
-   **7 - DEBUG**

It is possible to specify severity levels using either the numerical
values or the text values, but you should always specify severity levels
using the text values, because it is difficult to remember what a number
stands for. The use of the numerical values is deprecated as of version
2.5.0 and may be removed in one of the subsequent major updates.

## setuid

**Description:** Special-purpose action that initializes the USER
collection using the username provided as parameter.

**Action Group:** Non-disruptive

**Example:**

    SecRule ARGS:username ".*" "phase:2,id:137,t:none,pass,nolog,noauditlog,capture,setvar:session.username=%{TX.0},setuid:%{TX.0}"

After initialization takes place, the variable USERID will be available
for use in the subsequent rules. This action understands application
namespaces (configured using SecWebAppId), and will use one if it is
configured.

## setrsc

**Description:** Special-purpose action that initializes the RESOURCE
collection using a key provided as parameter.

**Action Group:** Non-disruptive

**Version:** 2.x-3.x

**Supported on libModSecurity:** Yes - as of 9cb3f2
[21](https://github.com/SpiderLabs/ModSecurity/commit/9cb3f23b5095cad7dfba8f140a44b9523f2be78b)

**Example:**

    SecAction "phase:1,pass,id:3,log,setrsc:'abcd1234'"

This action understands application namespaces (configured using
SecWebAppId), and will use one if it is configured.

## setsid

**Description:** Special-purpose action that initializes the SESSION
collection using the session token provided as parameter.

**Action Group:** Non-disruptive

**Example:**

    # Initialise session variables using the session cookie value 
    SecRule REQUEST_COOKIES:PHPSESSID !^$ "nolog,pass,id:138,setsid:%{REQUEST_COOKIES.PHPSESSID}"

Note

After the initialization takes place, the variable SESSION will be
available for use in the subsequent rules. This action understands
application namespaces (configured using SecWebAppId), and will use one
if it is configured.

Setsid takes an individual variable, not a collection. Variables within
an action, such as setsid, use the format \[collection\].\[variable\] .

## setenv

**Description:** Creates, removes, and updates environment variables
that can be accessed by Apache.

**Action Group:** Non-disruptive

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Examples:**

    SecRule RESPONSE_HEADERS:/Set-Cookie2?/ "(?i:(j?sessionid|(php)?sessid|(asp|jserv|jw)?session[-_]?(id)?|cf(id|token)|sid))" "phase:3,t:none,pass,id:139,nolog,setvar:tx.sessionid=%{matched_var}"
    SecRule TX:SESSIONID "!(?i:\;? ?httponly;?)" "phase:3,id:140,t:none,setenv:httponly_cookie=%{matched_var},pass,log,auditlog,msg:'AppDefect: Missing HttpOnly Cookie Flag.'"

    Header set Set-Cookie "%{httponly_cookie}e; HTTPOnly" env=httponly_cookie

Note : When used in a chain this action will be execute when an individual rule matches and not the entire chain.

## setvar

**Description:** Creates, removes, or updates a variable. Variable names
are case-insensitive.

**Action Group:** Non-disruptive

**Examples:** To create a variable and set its value to 1 (usually used
for setting flags), use: `setvar:TX.score`

To create a variable and initialize it at the same time, use:
`setvar:TX.score=10`

To remove a variable, prefix the name with an exclamation mark:
`setvar:!TX.score`

To increase or decrease variable value, use + and - characters in front
of a numerical value: `setvar:TX.score=+5`

Example from OWASP CRS:

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/* "\bsys\.user_catalog\b" \
            "phase:2,rev:'2.1.3',capture,t:none,t:urlDecodeUni,t:htmlEntityDecode,t:lowercase,t:replaceComments,t:compressWhiteSpace,ctl:auditLogParts=+E, \
    block,msg:'Blind SQL Injection Attack',id:'959517',tag:'WEB_ATTACK/SQL_INJECTION',tag:'WASCTC/WASC-19',tag:'OWASP_TOP_10/A1',tag:'OWASP_AppSensor/CIE1', \
    tag:'PCI/6.5.2',logdata:'%{TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.sql_injection_score=+%{tx.critical_anomaly_score}, \
    setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/SQL_INJECTION-%{matched_var_name}=%{tx.0}"

Note : When used in a chain this action will be executed when an individual rule matches and not the entire chain.This means that

\`\`\` SecRule REQUEST_FILENAME \"@contains /test.php\"
\"chain,id:7,phase:1,t:none,nolog,setvar:tx.auth_attempt=+1\"

`   SecRule ARGS_POST:action "@streq login" "t:none"`

\`\`\`

will increment every time that test.php is visited (regardless of the parameters submitted). If the desired goal is to set the variable only if the entire rule matches, it should be included in the last rule of the chain . For instance:

\`\`\` SecRule REQUEST_FILENAME \"@streq test.php\"
\"chain,id:7,phase:1,t:none,nolog\"

`   SecRule ARGS_POST:action "@streq login" "t:none,setvar:tx.auth_attempt=+1"`

\`\`\`

## skip

**Description:** Skips one or more rules (or chains) on successful
match.

**Action Group:** Flow

**Example:**

    # Require Accept header, but not from access from the localhost 
    SecRule REMOTE_ADDR "^127\.0\.0\.1$" "phase:1,skip:1,id:141" 

    # This rule will be skipped over when REMOTE_ADDR is 127.0.0.1 
    SecRule &REQUEST_HEADERS:Accept "@eq 0" "phase:1,id:142,deny,msg:'Request Missing an Accept Header'"

The skip action works only within the current processing phase and not
necessarily in the order in which the rules appear in the configuration
file. If you place a phase 2 rule after a phase 1 rule that uses skip,
it will not skip over the phase 2 rule. It will skip over the next phase
1 rule that follows it in the phase.

## skipAfter

Description: Skips one or more rules (or chains) on a successful match,
resuming rule execution with the first rule that follows the rule (or
marker created by SecMarker) with the provided ID.

**Action Group:** Flow

**Example:** The following rules implement the same logic as the skip
example, but using skipAfter:

    # Require Accept header, but not from access from the localhost 
    SecRule REMOTE_ADDR "^127\.0\.0\.1$" "phase:1,id:143,skipAfter:IGNORE_LOCALHOST" 

    # This rule will be skipped over when REMOTE_ADDR is 127.0.0.1 
    SecRule &REQUEST_HEADERS:Accept "@eq 0" "phase:1,deny,id:144,msg:'Request Missing an Accept Header'" 
    SecMarker IGNORE_LOCALHOST

Example from the OWASP ModSecurity CRS:

    SecMarker BEGIN_HOST_CHECK

        SecRule &REQUEST_HEADERS:Host "@eq 0" \
                "skipAfter:END_HOST_CHECK,phase:2,rev:'2.1.3',t:none,block,msg:'Request Missing a Host Header',id:'960008',tag:'PROTOCOL_VIOLATION/MISSING_HEADER_HOST',tag:'WASCTC/WASC-21', \
    tag:'OWASP_TOP_10/A7',tag:'PCI/6.5.10',severity:'5',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.notice_anomaly_score}, \
    setvar:tx.protocol_violation_score=+%{tx.notice_anomaly_score},setvar:tx.%{rule.id}-PROTOCOL_VIOLATION/MISSING_HEADER-%{matched_var_name}=%{matched_var}"

        SecRule REQUEST_HEADERS:Host "^$" \
                "phase:2,rev:'2.1.3',t:none,block,msg:'Request Missing a Host Header',id:'960008',tag:'PROTOCOL_VIOLATION/MISSING_HEADER_HOST',tag:'WASCTC/WASC-21',tag:'OWASP_TOP_10/A7', \
    tag:'PCI/6.5.10',severity:'5',setvar:'tx.msg=%{rule.msg}',setvar:tx.anomaly_score=+%{tx.notice_anomaly_score},setvar:tx.protocol_violation_score=+%{tx.notice_anomaly_score}, \
    setvar:tx.%{rule.id}-PROTOCOL_VIOLATION/MISSING_HEADER-%{matched_var_name}=%{matched_var}"

    SecMarker END_HOST_CHECK

The skipAfter action works only within the current processing phase and
not necessarily the order in which the rules appear in the configuration
file. If you place a phase 2 rule after a phase 1 rule that uses skip,
it will not skip over the phase 2 rule. It will skip over the next phase
1 rule that follows it in the phase.

## status

**Description:** Specifies the response status code to use with actions
deny and redirect.

**Action Group:** Data

**Example:**

    # Deny with status 403
    SecDefaultAction "phase:1,log,deny,id:145,status:403"

Status actions defined in Apache scope locations (such as Directory,
Location, etc\...) may be superseded by phase:1 action settings. The
Apache ErrorDocument directive will be triggered if present in the
configuration. Therefore if you have previously defined a custom error
page for a given status then it will be executed and its output
presented to the user.

## t

**Description:** This action is used to specify the transformation
pipeline to use to transform the value of each variable used in the rule
before matching.

**Action Group:** Non-disruptive

**Example:**

    SecRule ARGS "(asfunction|javascript|vbscript|data|mocha|livescript):" "id:146,t:none,t:htmlEntityDecode,t:lowercase,t:removeNulls,t:removeWhitespace"

Any transformation functions that you specify in a SecRule will be added
to the previous ones specified in SecDefaultAction. It is recommended
that you always use t:none in your rules, which prevents them depending
on the default configuration.

## tag

**Description:** Assigns a tag (category) to a rule or a chain.

**Action Group:** Meta-data

**Example:**

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/* "\bgetparentfolder\b" \
        "phase:2,rev:'2.1.3',capture,t:none,t:htmlEntityDecode,t:compressWhiteSpace,t:lowercase,ctl:auditLogParts=+E,block,msg:'Cross-site Scripting (XSS) Attack',id:'958016',tag:'WEB_ATTACK/XSS',tag:'WASCTC/WASC-8',tag:'WASCTC/WASC-22',tag:'OWASP_TOP_10/A2',tag:'OWASP_AppSensor/IE1',tag:'PCI/6.5.1',logdata:'% \
    {TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.xss_score=+%{tx.critical_anomaly_score},setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/XSS-%{matched_var_name}=%{tx.0}"

The tag information appears along with other rule metadata. The purpose
of the tagging mechanism to allow easy automated categorization of
events. Multiple tags can be specified on the same rule. Use forward
slashes to create a hierarchy of categories (as in the example). Since
ModSecurity 2.6.0 tag supports macro expansion.

## ver

**Description:** Specifies the rule set version.

**Action Group:** Meta-data

**Version:** 2.7

**Example:**

    SecRule REQUEST_FILENAME|ARGS_NAMES|ARGS|XML:/* "\bgetparentfolder\b" \
        "phase:2,ver:'CRS/2.2.4,capture,t:none,t:htmlEntityDecode,t:compressWhiteSpace,t:lowercase,ctl:auditLogParts=+E,block,msg:'Cross-site Scripting (XSS) Attack',id:'958016',tag:'WEB_ATTACK/XSS',tag:'WASCTC/WASC-8',tag:'WASCTC/WASC-22',tag:'OWASP_TOP_10/A2',tag:'OWASP_AppSensor/IE1',tag:'PCI/6.5.1',logdata:'% \
    {TX.0}',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.xss_score=+%{tx.critical_anomaly_score},setvar:tx.anomaly_score=+%{tx.critical_anomaly_score},setvar:tx.%{rule.id}-WEB_ATTACK/XSS-%{matched_var_name}=%{tx.0}"

## xmlns

**Description:** Configures an XML namespace, which will be used in the
execution of XPath expressions.

**Action Group:** Data

**Example:**

    SecRule REQUEST_HEADERS:Content-Type "text/xml" "phase:1,id:147,pass,ctl:requestBodyProcessor=XML,ctl:requestBodyAccess=On, \
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    SecRule XML:/soap:Envelope/soap:Body/q1:getInput/id() "123" phase:2,deny,id:148

# Operators

This section documents the operators currently available in ModSecurity.

## beginsWith

**Description:** Returns true if the parameter string is found at the
beginning of the input. Macro expansion is performed on the parameter
string before comparison.

**Example:**

    # Detect request line that does not begin with "GET" 
    SecRule REQUEST_LINE "!@beginsWith GET" "id:149"

## contains

**Description:** Returns true if the parameter string is found anywhere
in the input. Macro expansion is performed on the parameter string
before comparison.

**Example:**

    # Detect ".php" anywhere in the request line 
    SecRule REQUEST_LINE "@contains .php" "id:150"

## containsWord

**Description:** Returns true if the parameter string (with word
boundaries) is found anywhere in the input. Macro expansion is performed
on the parameter string before comparison.

**Example:**

    # Detect "select" anywhere in ARGS 
    SecRule ARGS "@containsWord select" "id:151"

Would match on -\
-1 union **select** BENCHMARK(2142500,MD5(CHAR(115,113,108,109,97,112)))
FROM wp_users WHERE ID=1 and (ascii(substr(user_login,1,1))&0x01=0) from
wp_users where ID=1\--

But not on -\
Your site has a wide **select**ion of computers.

## detectSQLi

**Description:** Returns true if SQL injection payload is found. This
operator uses LibInjection to detect SQLi attacks.

**Version:** 2.7.4

**Example:**

    # Detect SQL Injection inside request uri data" 
    SecRule REQUEST_URI "@detectSQLi" "id:152"

Note : This operator supports the \"capture\" action.

## detectXSS

**Description:** Returns true if XSS injection is found. This operator
uses LibInjection to detect XSS attacks.

**Version:** 2.8.0

**Example:**

    # Detect XSS Injection inside request body 
    SecRule REQUEST_BODY "@detectXSS" "id:12345,log,deny"

Note : This operator supports the \"capture\" action.

## endsWith

**Description:** Returns true if the parameter string is found at the
end of the input. Macro expansion is performed on the parameter string
before comparison.

**Example:**

    # Detect request line that does not end with "HTTP/1.1" 
    SecRule REQUEST_LINE "!@endsWith HTTP/1.1" "id:152"

## fuzzyHash

**Description:** The fuzzyHash operator uses the ssdeep, which is a
program for computing context triggered piecewise hashes (CTPH). Also
called fuzzy hashes, CTPH can match inputs that have homologies. Such
inputs have sequences of identical bytes in the same order, although
bytes in between these sequences may be different in both content and
length.

For further information on ssdeep, visit its site:
<http://ssdeep.sourceforge.net/>

**Version:** v2.9.0-RC1-2.9.x

**Supported on libModSecurity:** TBI

**Example:**

    SecRule REQUEST_BODY "\@fuzzyHash /path/to/ssdeep/hashes.txt 6" "id:192372,log,deny"

## eq

**Description:** Performs numerical comparison and returns true if the
input value is equal to the provided parameter. Macro expansion is
performed on the parameter string before comparison.

**Example:**

    # Detect exactly 15 request headers 
    SecRule &REQUEST_HEADERS_NAMES "@eq 15" "id:153"

Note : If a value is provided that cannot be converted to an integer (i.e a string) this operator will treat that value as 0.

## ge

**Description:** Performs numerical comparison and returns true if the
input value is greater than or equal to the provided parameter. Macro
expansion is performed on the parameter string before comparison.

**Example:**

    # Detect 15 or more request headers 
    SecRule &REQUEST_HEADERS_NAMES "@ge 15" "id:154"

Note : If a value is provided that cannot be converted to an integer (i.e a string) this operator will treat that value as 0.

## geoLookup

**Description:** Performs a geolocation lookup using the IP address in
input against the geolocation database previously configured using
SecGeoLookupDb. If the lookup is successful, the obtained information is
captured in the GEO collection.

**Example:** The geoLookup operator matches on success and is thus best
used in combination with nolog,pass. If you wish to block on a failed
lookup (which may be over the top, depending on how accurate the
geolocation database is), the following example demonstrates how best to
do it:

    # Configure geolocation database 
    SecGeoLookupDb /path/to/GeoLiteCity.dat 
    ... 
    # Lookup IP address 
    SecRule REMOTE_ADDR "@geoLookup" "phase:1,id:155,nolog,pass"

    # Block IP address for which geolocation failed
     SecRule &GEO "@eq 0" "phase:1,id:156,deny,msg:'Failed to lookup IP'"

See the GEO variable for an example and more information on various
fields available.

## gsbLookup

**Description:** Performs a local lookup of Google\'s Safe Browsing
using URLs in input against the GSB database previously configured using
SecGsbLookupDb. When combined with capture operator it will save the
matched url into tx.0 variable.

**Syntax:** `SecRule TARGET "@gsbLookup REGEX" ACTIONS`

**Version:** 2.6

**Supported on libModSecurity:** TBD

**Example:** The gsbLookup operator matches on success and is thus best
used in combination with a block or redirect action. If you wish to
block on successful lookups, the following example demonstrates how best
to do it:

    # Configure Google Safe Browsing database 
    SecGsbLookupDb /path/to/GsbMalware.dat 
    ... 
    # Check response bodies for malicious links
    SecRule RESPONSE_BODY "@gsbLookup =\"https?\:\/\/(.*?)\"" "phase:4,id:157,capture,log,block,msg:'Bad url detected in RESPONSE_BODY (Google Safe Browsing Check)',logdata:'http://www.google.com/safebrowsing/diagnostic?site=%{tx.0}'"

Note : This operator supports the \"capture\" action.

## gt

**Description:** Performs numerical comparison and returns true if the
input value is greater than the operator parameter. Macro expansion is
performed on the parameter string before comparison.

**Example:**

    # Detect more than 15 headers in a request 
    SecRule &REQUEST_HEADERS_NAMES "@gt 15" "id:158"

Note : If a value is provided that cannot be converted to an integer (i.e a string) this operator will treat that value as 0.

## inspectFile

**Description:** Executes an external program for every variable in the
target list. The contents of the variable is provided to the script as
the first parameter on the command line. The program must be specified
as the first parameter to the operator. As of version 2.5.0, if the
supplied program filename is not absolute, it is treated as relative to
the directory in which the configuration file resides. Also as of
version 2.5.0, if the filename is determined to be a Lua script (based
on its .lua extension), the script will be processed by the internal Lua
engine. Internally processed scripts will often run faster (there is no
process creation overhead) and have full access to the transaction
context of ModSecurity.

The \@inspectFile operator was initially designed for file inspection
(hence the name), but it can also be used in any situation that requires
decision making using external logic.

The OWASP ModSecurity Core Rule Set (CRS) includes a utility script in
the /util directory called runav.pl
[22](http://mod-security.svn.sourceforge.net/viewvc/mod-security/crs/trunk/util/)
that allows the file approval mechanism to integrate with the ClamAV
virus scanner. This is especially handy to prevent viruses and exploits
from entering the web server through file upload.

    #!/usr/bin/perl
    #
    # runav.pl
    # Copyright (c) 2004-2011 Trustwave
    #
    # This script is an interface between ModSecurity and its
    # ability to intercept files being uploaded through the
    # web server, and ClamAV


    $CLAMSCAN = "clamscan";

    if ($#ARGV != 0) {
        print "Usage: runav.pl <filename>\n";
        exit;
    }

    my ($FILE) = shift @ARGV;

    $cmd = "$CLAMSCAN --stdout --no-summary $FILE";
    $input = `$cmd`;
    $input =~ m/^(.+)/;
    $error_message = $1;

    $output = "0 Unable to parse clamscan output [$1]";

    if ($error_message =~ m/: Empty file\.?$/) {
        $output = "1 empty file";
    }
    elsif ($error_message =~ m/: (.+) ERROR$/) {
        $output = "0 clamscan: $1";
    }
    elsif ($error_message =~ m/: (.+) FOUND$/) {
        $output = "0 clamscan: $1";
    }
    elsif ($error_message =~ m/: OK$/) {
        $output = "1 clamscan: OK";
    }

    print "$output\n";

**Example:** Using the runav.pl script:

    # Execute external program to validate uploaded files 
    SecRule FILES_TMPNAMES "@inspectFile /path/to/util/runav.pl" "id:159"

Example of using Lua script (placed in the same directory as the
configuration file):

    SecRule FILES_TMPNAMES "@inspectFile inspect.lua" "id:160"

The contents of inspect.lua:

    function main(filename)
        -- Do something to the file to verify it. In this example, we
        -- read up to 10 characters from the beginning of the file.
        local f = io.open(filename, "rb");
        local d = f:read(10);
        f:close();
       
        -- Return null if there is no reason to believe there is ansything
        -- wrong with the file (no match). Returning any text will be taken
        -- to mean a match should be trigerred.
        return null;
    end

Note : Starting in version 2.9 ModSecurity will not fill the FILES_TMPNAMES variable unless SecTmpSaveUploadedFiles directive is On, or the SecUploadKeepFiles directive is set to RelevantOnly.

```{=html}
<!-- -->
```

Note: Use \@inspectFile with caution. It may not be safe to use \@inspectFile with variables other than FILES_TMPNAMES. Other variables such as \"FULL_REQUEST\" may contains content that force your platform to fork process out of your control, making possible to an attacker to execute code using the same permissions of your web server. For other variables you may want to look at the Lua script engine. This observation was brought to our attention by \"Gryzli\", on our users mailing list.

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Reference:**
<http://blog.spiderlabs.com/2010/10/advanced-topic-of-the-week-preventing-malicious-pdf-file-uploads.html>

**Reference:**
<http://sourceforge.net/p/mod-security/mailman/mod-security-users/?viewmonth=201512>

## ipMatch

**Description:** Performs a fast ipv4 or ipv6 match of REMOTE_ADDR
variable data. Can handle the following formats:

-   Full IPv4 Address - 192.168.1.100
-   Network Block/CIDR Address - 192.168.1.0/24
-   Full IPv6 Address - 2001:db8:85a3:8d3:1319:8a2e:370:7348
-   Network Block/CIDR Address - 2001:db8:85a3:8d3:1319:8a2e:370:0/24

**Version:** 2.7

**Examples:**

Individual Address:

    SecRule REMOTE_ADDR "@ipMatch 192.168.1.100" "id:161"

Multiple Addresses w/network block:

    SecRule REMOTE_ADDR "@ipMatch 192.168.1.100,192.168.1.50,10.10.50.0/24" "id:162"

## ipMatchF

short alias for ipMatchFromFile

**Version:** 2.7

## ipMatchFromFile

**Description:** Performs a fast ipv4 or ipv6 match of REMOTE_ADDR
variable, loading data from a file. Can handle the following formats:

-   Full IPv4 Address - 192.168.1.100
-   Network Block/CIDR Address - 192.168.1.0/24
-   Full IPv6 Address - 2001:db8:85a3:8d3:1319:8a2e:370:7348
-   Network Block/CIDR Address - 2001:db8:85a3:8d3:1319:8a2e:370:0/24

**Version:** 2.7

**Examples:**

    SecRule REMOTE_ADDR "@ipMatchFromFile ips.txt" "id:163"

The file ips.txt may contain:

    192.168.0.1
    172.16.0.0/16
    10.0.0.0/8

Note : As of v2.9.0-RC1 this operator also supports to load content served by an HTTPS server.

```{=html}
<!-- -->
```

Note : When used with content served by a HTTPS server, the directive SecRemoteRulesFailAction can be used to configure a warning instead of an abort, when the remote content could not be retrieved.

## le

**Description:** Performs numerical comparison and returns true if the
input value is less than or equal to the operator parameter. Macro
expansion is performed on the parameter string before comparison.

**Example**:

    # Detect 15 or fewer headers in a request 
    SecRule &REQUEST_HEADERS_NAMES "@le 15" "id:164"

Note : If a value is provided that cannot be converted to an integer (i.e a string) this operator will treat that value as 0.

## lt

**Description:** Performs numerical comparison and returns true if the
input value is less than to the operator parameter. Macro expansion is
performed on the parameter string before comparison.

**Example:**

    # Detect fewer than 15 headers in a request 
    SecRule &REQUEST_HEADERS_NAMES "@lt 15" "id:165"

Note : If a value is provided that cannot be converted to an integer (i.e a string) this operator will treat that value as 0.

## noMatch

**Description:** Will force the rule to always return false.

## pm

**Description:** Performs a case-insensitive match of the provided
phrases against the desired input value. The operator uses a set-based
matching algorithm (Aho-Corasick), which means that it will match any
number of keywords in parallel. When matching of a large number of
keywords is needed, this operator performs much better than a regular
expression.

**Example:**

    # Detect suspicious client by looking at the user agent identification 
    SecRule REQUEST_HEADERS:User-Agent "@pm WebZIP WebCopier Webster WebStripper ... SiteSnagger ProWebWalker CheeseBot" "id:166"

Note : Starting on ModSecurity v2.6.0 this operator supports a snort/suricata content style. ie: \"@pm A\|42\|C\|44\|F\".

```{=html}
<!-- -->
```

Note : This operator does not support macro expansion (as of ModSecurity v2.9.1).

```{=html}
<!-- -->
```

Note : This operator supports the \"capture\" action.

## pmf

Short alias for pmFromFile.

## pmFromFile

**Description:** Performs a case-insensitive match of the provided
phrases against the desired input value. The operator uses a set-based
matching algorithm (Aho-Corasick), which means that it will match any
number of keywords in parallel. When matching of a large number of
keywords is needed, this operator performs much better than a regular
expression.

This operator is the same as \@pm, except that it takes a list of files
as arguments. It will match any one of the phrases listed in the file(s)
anywhere in the target value.

**Example:**

    # Detect suspicious user agents using the keywords in 
    # the files /path/to/blacklist1 and blacklist2 (the latter 
    # must be placed in the same folder as the configuration file) 
    SecRule REQUEST_HEADERS:User-Agent "@pmFromFile /path/to/blacklist1 blacklist2" "id:167"

Notes:

1.  Files must contain exactly one phrase per line. End of line markers
    (both LF and CRLF) will be stripped from each phrase and any
    whitespace trimmed from both the beginning and the end. Empty lines
    and comment lines (those beginning with the \# character) will be
    ignored.
2.  To allow easier inclusion of phrase files with rule sets, relative
    paths may be used to the phrase files. In this case, the path of the
    file containing the rule is prepended to the phrase file path.
3.  The \@pm operator phrases do not support metacharacters.
4.  Because this operator does not check for boundaries when matching,
    false positives are possible in some cases. For example, if you want
    to use \@pm for IP address matching, the phrase 1.2.3.4 will
    potentially match more than one IP address (e.g., it will also match
    1.2.3.40 or 1.2.3.41). To avoid the false positives, you can use
    your own boundaries in phrases. For example, use /1.2.3.4/ instead
    of just 1.2.3.4. Then, in your rules, also add the boundaries where
    appropriate. You will find a complete example in the example.

```{=html}
<!-- -->
```
    # Prepare custom REMOTE_ADDR variable 
    SecAction "phase:1,id:168,nolog,pass,setvar:tx.REMOTE_ADDR=/%{REMOTE_ADDR}/"

    # Check if REMOTE_ADDR is blacklisted 
    SecRule TX:REMOTE_ADDR "@pmFromFile blacklist.txt" "phase:1,id:169,deny,msg:'Blacklisted IP address'" 

The file blacklist.txt may contain:

    # ip-blacklist.txt contents:
    # NOTE: All IPs must be prefixed/suffixed with "/" as the rules
    #   will add in this character as a boundary to ensure
    #   the entire IP is matched.
    # SecAction "phase:1,id:170,pass,nolog,setvar:tx.remote_addr='/%{REMOTE_ADDR}/'"
    /1.2.3.4/ 
    /5.6.7.8/

Warning : Before ModSecurity 2.5.12, the \@pmFromFile operator understood only the LF line endings and did not trim the whitespace from phrases. If you are using an older version of ModSecurity, you should take care when editing the phrase files to avoid using the undesired characters in patterns.e files should be one phrase per line. End of line markers will be stripped from the phrases (LF and CRLF), and whitespace is trimmed from both sides of the phrases. Empty lines and comment lines (beginning with a \'#\') are ignored. To allow easier inclusion of phrase files with rulesets, relative paths may be used to the phrase files. In this case, the path of the file containing the rule is prepended to the phrase file path.

```{=html}
<!-- -->
```

Note : Starting on ModSecurity v2.6.0 this operator supports a snort/suricata content style. ie: \"A\|42\|C\|44\|F\".

```{=html}
<!-- -->
```

Note II : As of v2.9.0-RC1 this operator also supports to load content served by an HTTPS server. However, only one url can be used at a time.

## rbl

**Description:** Looks up the input value in the RBL (real-time block
list) given as parameter. The parameter can be an IPv4 address or a
hostname.

**Example:**

    SecRule REMOTE_ADDR "@rbl sbl-xbl.spamhaus.org" "phase:1,id:171,t:none,pass,nolog,auditlog,msg:'RBL Match for SPAM Source',tag:'AUTOMATION/MALICIOUS',severity:'2',setvar:'tx.msg=%{rule.msg}',setvar:tx.automation_score=+%{tx.warning_anomaly_score},setvar:tx.anomaly_score=+%{tx.warning_anomaly_score}, \
    setvar:tx.%{rule.id}-AUTOMATION/MALICIOUS-%{matched_var_name}=%{matched_var},setvar:ip.spammer=1,expirevar:ip.spammer=86400,setvar:ip.previous_rbl_check=1,expirevar:ip.previous_rbl_check=86400,skipAfter:END_RBL_CHECK"

Note : If the RBL used is dnsbl.httpbl.org (Honeypot Project RBL) then the SecHttpBlKey directive must specify the user\'s registered API key.\
Note : If the RBL used is either multi.uribl.com or zen.spamhaus.org combined RBLs, it is possible to also parse the return codes in the last octet of the DNS response to identify which specific RBL the IP was found in.

```{=html}
<!-- -->
```

Note : This operator supports the \"capture\" action.

## rsub

**Description**: Performs regular expression data substitution when
applied to either the STREAM_INPUT_BODY or STREAM_OUTPUT_BODY variables.
This operator also supports macro expansion. Starting with ModSecurity
2.7.0 this operator supports the syntax \|hex\| allowing users to use
special chars like \\n \\r

**Syntax:** `@rsub s/regex/str/[id]`

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Examples:** Removing HTML Comments from response bodies:

    SecStreamOutBodyInspection On
    SecRule STREAM_OUTPUT_BODY "@rsub s/<!--.*?-->/ /" "phase:4,id:172,t:none,nolog,pass"

Note : If you plan to manipulate live data by using \@rsub with the STREAM\_ variables, you must also enable SecContentInjection directive.

Regular expressions are handled by the PCRE library
[23](http://www.pcre.org). ModSecurity compiles its regular expressions
with the following settings:

1.  The entire input is treated as a single line, even when there are
    newline characters present.
2.  All matches are case-sensitive. If you wish to perform
    case-insensitive matching, you can either use the lowercase
    transformation function or force case-insensitive matching by
    prefixing the regular expression pattern with the (?i) modifier (a
    PCRE feature; you will find many similar features in the PCRE
    documentation). Also a flag \[d\] should be used if you want to
    escape the regex string chars when use macro expansion.
3.  The PCRE_DOTALL and PCRE_DOLLAR_ENDONLY flags are set during
    compilation, meaning that a single dot will match any character,
    including the newlines, and a \$ end anchor will not match a
    trailing newline character.

Regular expressions are a very powerful tool. You are strongly advised
to read the PCRE documentation to get acquainted with its features.

Note : This operator supports the \"capture\" action.

## rx

**Description**: Performs a regular expression match of the pattern
provided as parameter. **This is the default operator; the rules that do
not explicitly specify an operator default to \@rx**.

**Examples:**

    # Detect Nikto 
    SecRule REQUEST_HEADERS:User-Agent "@rx nikto" phase:1,id:173,t:lowercase

    # Detect Nikto with a case-insensitive pattern 
    SecRule REQUEST_HEADERS:User-Agent "@rx (?i)nikto" phase:1,id:174,t:none

    # Detect Nikto with a case-insensitive pattern 
    SecRule REQUEST_HEADERS:User-Agent "(?i)nikto" "id:175"

Regular expressions are handled by the PCRE library
[24](http://www.pcre.org). ModSecurity compiles its regular expressions
with the following settings:

1.  The entire input is treated as a single line, even when there are
    newline characters present.
2.  All matches are case-sensitive. If you wish to perform
    case-insensitive matching, you can either use the lowercase
    transformation function or force case-insensitive matching by
    prefixing the regular expression pattern with the (?i) modifier (a
    PCRE feature; you will find many similar features in the PCRE
    documentation).
3.  The PCRE_DOTALL and PCRE_DOLLAR_ENDONLY flags are set during
    compilation, meaning that a single dot will match any character,
    including the newlines, and a \$ end anchor will not match a
    trailing newline character.

Regular expressions are a very powerful tool. You are strongly advised
to read the PCRE documentation to get acquainted with its features.

Note : This operator supports the \"capture\" action.

## streq

**Description:** Performs a string comparison and returns true if the
parameter string is identical to the input string. Macro expansion is
performed on the parameter string before comparison.

**Example:**

    # Detect request parameters "foo" that do not # contain "bar", exactly. 
    SecRule ARGS:foo "!@streq bar" "id:176"

## strmatch

**Description:** Performs a string match of the provided word against
the desired input value. The operator uses the pattern matching
Boyer-Moore-Horspool algorithm, which means that it is a single pattern
matching operator. This operator performs much better than a regular
expression.

**Example:**

    # Detect suspicious client by looking at the user agent identification 
    SecRule REQUEST_HEADERS:User-Agent "@strmatch WebZIP" "id:177"

Note : Starting on ModSecurity v2.6.0 this operator supports a snort/suricata content style. ie: \"@strmatch A\|42\|C\|44\|F\".

## unconditionalMatch

**Description:** Will force the rule to always return true. This is
similar to SecAction however all actions that occur as a result of a
rule matching will fire such as the setting of MATCHED_VAR. This can
also be part a chained rule.

**Example:**

    SecRule REMOTE_ADDR "@unconditionalMatch" "id:1000,phase:1,pass,nolog,t:hexEncode,setvar:TX.ip_hash=%{MATCHED_VAR}"

## validateByteRange

**Description:** Validates that the byte values used in input fall into
the range specified by the operator parameter. This operator matches on
an input value that contains bytes that are not in the specified range.

**Example:**

    # Enforce very strict byte range for request parameters (only 
    # works for the applications that do not use the languages other 
    # than English). 
    SecRule ARGS "@validateByteRange 10, 13, 32-126" "id:178"

The validateByteRange is most useful when used to detect the presence of
NUL bytes, which don't have a legitimate use, but which are often used
as an evasion technique.

    # Do not allow NUL bytes 
    SecRule ARGS "@validateByteRange 1-255" "id:179"

Note : You can force requests to consist only of bytes from a certain byte range. This can be useful to avoid stack overflow attacks (since they usually contain \"random\" binary content). Default range values are 0 and 255, i.e. all byte values are allowed. This directive does not check byte range in a POST payload when multipart/form-data encoding (file upload) is used. Doing so would prevent binary files from being uploaded. However, after the parameters are extracted from such request they are checked for a valid range.

validateByteRange is similar to the ModSecurity 1.X
SecFilterForceByteRange Directive however since it works in a rule
context, it has the following differences:

-   You can specify a different range for different variables.
-   It has an \"event\" context (id, msg\....)
-   It is executed in the flow of rules rather than being a built in
    pre-check.

## validateDTD

**Description:** Validates the XML DOM tree against the supplied DTD.
The DOM tree must have been built previously using the XML request body
processor. This operator matches when the validation fails.

**Example:**

    # Parse the request bodies that contain XML 
    SecRule REQUEST_HEADERS:Content-Type ^text/xml$ "phase:1,id:180,nolog,pass,t:lowercase,ctl:requestBodyProcessor=XML"

    # Validate XML payload against DTD 
    SecRule XML "@validateDTD /path/to/xml.dtd" "phase:2,id:181,deny,msg:'Failed DTD validation'"

**NOTE:** You must enable the `SecXmlExternalEntity` directive.

## validateHash

**Description:** Validates REQUEST_URI that contains data protected by
the hash engine.

**Version:** 2.x

**Supported on libModSecurity:** TBI

**Example:**

    # Validates requested URI that matches a regular expression.
    SecRule REQUEST_URI "@validatehash "product_info|product_list" "phase:1,deny,id:123456"

## validateSchema

**Description:** Validates the XML DOM tree against the supplied XML
Schema. The DOM tree must have been built previously using the XML
request body processor. This operator matches when the validation fails.

**Example:**

    # Parse the request bodies that contain XML 
    SecRule REQUEST_HEADERS:Content-Type ^text/xml$ "phase:1,id:190,nolog,pass,t:lowercase,ctl:requestBodyProcessor=XML"

    # Validate XML payload against DTD 
    SecRule XML "@validateSchema /path/to/xml.xsd" "phase:2,id:191,deny,msg:'Failed DTD validation'"

**NOTE:** You must enable the `SecXmlExternalEntity` directive.

## validateUrlEncoding

**Description**: Validates the URL-encoded characters in the provided
input string.

**Example:**

    # Validate URL-encoded characters in the request URI 
    SecRule REQUEST_URI_RAW "@validateUrlEncoding" "id:192"

ModSecurity will automatically decode the URL-encoded characters in
request parameters, which means that there is little sense in applying
the \@validateUrlEncoding operator to them ---that is, unless you know
that some of the request parameters were URL-encoded more than once. Use
this operator against raw input, or against the input that you know is
URL-encoded. For example, some applications will URL-encode cookies,
although that's not in the standard. Because it is not in the standard,
ModSecurity will neither validate nor decode such encodings.

## validateUtf8Encoding

**Description:** Check whether the input is a valid UTF-8 string.

**Example:**

    # Make sure all request parameters contain only valid UTF-8 
    SecRule ARGS "@validateUtf8Encoding" "id:193"

The \@validateUtf8Encoding operator detects the following problems:

Not enough bytes : UTF-8 supports two-, three-, four-, five-, and six-byte encodings. ModSecurity will locate cases when one or more bytes is/are missing from a character.\
Invalid characters : The two most significant bits in most characters should be fixed to 0x80. Some attack techniques use different values as an evasion technique.\
Overlong characters : ASCII characters are mapped directly into UTF-8, which means that an ASCII character is one UTF-8 character at the same time. However, in UTF-8 many ASCII characters can also be encoded with two, three, four, five, and six bytes. This is no longer legal in the newer versions of Unicode, but many older implementations still support it. The use of overlong UTF-8 characters is common for evasion.

```{=html}
<!-- -->
```

Notes :

-   Most, but not all applications use UTF-8. If you are dealing with an
    application that does, validating that all request parameters are
    valid UTF-8 strings is a great way to prevent a number of evasion
    techniques that use the assorted UTF-8 weaknesses. False positives
    are likely if you use this operator in an application that does not
    use UTF-8.
-   Many web servers will also allow UTF-8 in request URIs. If yours
    does, you can verify the request URI using \@validateUtf8Encoding.

## verifyCC

**Description:** Detects credit card numbers in input. This operator
will first use the supplied regular expression to perform an initial
match, following up with the Luhn algorithm calculation to minimize
false positives.

**Example:**

    # Detect credit card numbers in parameters and 
    # prevent them from being logged to audit log 
    SecRule ARGS "@verifyCC \d{13,16}" "phase:2,id:194,nolog,pass,msg:'Potential credit card number',sanitiseMatched"

Note : This operator supports the \"capture\" action.

## verifyCPF

**Description:** Detects CPF numbers (Brazilian social number) in input.
This operator will first use the supplied regular expression to perform
an initial match, following up with an algorithm calculation to minimize
false positives.

**Example:**

    # Detect CPF numbers in parameters and 
    # prevent them from being logged to audit log 
    SecRule ARGS "@verifyCPF /^([0-9]{3}\.){2}[0-9]{3}-[0-9]{2}$/" "phase:2,id:195,nolog,pass,msg:'Potential CPF number',sanitiseMatched"

**Version:** 2.6-3.x

**Supported on libModSecurity:** Yes

Note : This operator supports the \"capture\" action.

## verifySSN

**Description:** Detects US social security numbers (SSN) in input. This
operator will first use the supplied regular expression to perform an
initial match, following up with an SSN algorithm calculation to
minimize false positives.

**Example:**

    # Detect social security numbers in parameters and 
    # prevent them from being logged to audit log 
    SecRule ARGS "@verifySSN \d{3}-?\d{2}-?\d{4}" "phase:2,id:196,nolog,pass,msg:'Potential social security number',sanitiseMatched"

**Version:** 2.6-3.x

**Supported on libModSecurity:** Yes

**SSN Format**:

A Social Security number is broken up into 3 sections:

-   Area (3 digits)
-   Group (2 digits)
-   Serial (4 digits)

**verifySSN checks:**

-   Must have 9 digits
-   Cannot be a sequence number (ie,, 123456789, 012345678)
-   Cannot be a repetition sequence number ( ie 11111111 , 222222222)
-   Cannot have area and/or group and/or serial zeroed sequences
-   Area code must be less than 740
-   Area code must be different then 666

Note : This operator supports the \"capture\" action.

## within

**Description:** Returns true if the input value (the needle) is found
anywhere within the \@within parameter (the haystack). Macro expansion
is performed on the parameter string before comparison.

**Example:**

    # Detect request methods other than GET, POST and HEAD 
    SecRule REQUEST_METHOD "!@within GET,POST,HEAD"

NOTE: There are no delimiters for this operator, it is therefore often necessary to artificially impose some; this can be done using setvar. For instance in the example below, without the imposed delimiters (of \'/\') this rule would also match on the \'range\' header (along with many other combinations), since \'range\' is within the provided parameter. With the imposed delimiters, the rule would check for \'/range/\' when the range header is provided, and therefore would not match since \'/range/ is not part of the \@within parameter.

\`\`\` SecRule REQUEST_HEADERS_NAMES \"@rx \^.\*\$\" \\ \"chain,\\
id:1,\\ block,\\ t:lowercase,\\ setvar:\'tx.header_name=/%{tx.0}/\'\"

`  SecRule TX:header_name "@within /proxy/ /lock-token/ /content-range/ /translate/ /if/" "t:none"`

\`\`\`

# Macro Expansion {#macro_expansion}

Macros allow for using place holders in rules that will be expanded out
to their values at runtime. Currently only variable expansion is
supported, however more options may be added in future versions of
ModSecurity.

Format:

    %{VARIABLE}
    %{COLLECTION.VARIABLE}

Macro expansion can be used in actions such as initcol, setsid, setuid,
setvar, setenv, logdata. Operators that are evaluated at runtime support
expansion and are noted above. Such operators include \@beginsWith,
\@endsWith, \@contains, \@within and \@streq. You can use macro
expansion for operators that are \"compiled\" such \@rx, etc. however
you will have some impact in efficiency.

Some values you may want to expand include: TX, REMOTE_ADDR, USERID,
HIGHEST_SEVERITY, MATCHED_VAR, MATCHED_VAR_NAME, MULTIPART_STRICT_ERROR,
RULE, SESSION, USERID, among others.

# Persistent Storage {#persistent_storage}

At this time it is only possible to have five collections in which data
is stored persistently (i.e. data available to multiple requests). These
are: GLOBAL, RESOURCE, IP, SESSION and USER.

Every collection contains several built-in variables that are available
and are read-only unless otherwise specified:

1.  **CREATE_TIME** - date/time of the creation of the collection.
2.  **IS_NEW** - set to 1 if the collection is new (not yet persisted)
    otherwise set to 0.
3.  **KEY** - the value of the initcol variable (the client\'s IP
    address in the example).
4.  **LAST_UPDATE_TIME** - date/time of the last update to the
    collection.
5.  **TIMEOUT** - date/time in seconds when the collection will be
    updated on disk from memory (if no other updates occur). This
    variable may be set if you wish to specifiy an explicit expiration
    time (default is 3600 seconds). The TIMEOUT is updated every time
    that the values of an entry is changed.
6.  **UPDATE_COUNTER** - how many times the collection has been updated
    since creation.
7.  **UPDATE_RATE** - is the average rate updates per minute since
    creation.

To create a collection to hold session variables (SESSION) use action
setsid. To create a collection to hold user variables (USER) use action
setuid. To create a collection to hold client address variables (IP),
global data or resource-specific data, use action initcol.

Note : Persistent collections can only be initialized once per transaction.

```{=html}
<!-- -->
```

Note : ModSecurity implements atomic updates of persistent variables only for integer variables (counters) at this time. Variables are read from storage whenever initcol is encountered in the rules and persisted at the end of request processing. Counters are adjusted by applying a delta generated by re-reading the persisted data just before being persisted. This keeps counter data consistent even if the counter was modified and persisted by another thread/process during the transaction.

```{=html}
<!-- -->
```

Note : ModSecurity uses a Berkley Database (SDBM) for persistent storage. This type of database is generally limited to storing a maximum of 1008 bytes per key. This may be a limitation if you are attempting to store a considerable amount of data in variables for a single key. Some of this limitation is planned to be reduced in a future version of ModSecurity.

# Miscellaneous Topics {#miscellaneous_topics}

## Logging in Apache via mod_log_config {#logging_in_apache_via_mod_log_config}

The ModSecurity variables are accessible from Apache\'s mod_log_config
(-\> Apache Access Log). The entries take the form %{VARIABLE}M. Apache
writes these logs at the very end of a transaction after the record in
the ModSecurity audit log has been written. It is thus possible to log
variables, that are only defined after the writing of the audit Log.

Examples Apache mod_log_config:

    LogFormat "%t %{UNIQUE_ID}e %{MULTIPART_STRICT_ERROR}M %{TX.ANOMALY_SCORE}M" custom-format

## Precedence of ModSecurity over other Apache modules {#precedence_of_modsecurity_over_other_apache_modules}

ModSecurity rules run in one of five phases. The first two phases are
executed as the request is being read, the third and the fourth phase
are executed after the response has been generated and the fifth phase
when the response has been sent and the logfile has been written.

The various phases are hooked into the Apache request lifecycle together
with the other Apache modules. On each hook, there can be more than one
module being executed. This is where precedence comes into play.

Precedence is assigned at compile time and mostly hard-coded into the
ModSecurity source code. The compilation directive
\--enable-request-early can used to move the processing of the
ModSecurity phase 1 to a different hook (see above).

When examining the response, ModSecurity tries to be as early as
possible. For example, the phase 3 and phase 4 will run before
mod_headers with its \_Header\_ directive. However, when calling
\_Header\_ with the keyword \_early\_, the precedence is raised and the
directive is executed before ModSecurity phase 3. So if you want to edit
HTTP response headers with mod_headers (adding the secure-flag to
cookies springs to mind), you will usually have to wait until
ModSecurity phase 5, before you can examine the effect of the header
manipulation with ModSecurity.

Also see Processing Phases (above).

# A Recommended Base Configuration {#a_recommended_base_configuration}

The recommended configuration file which handles the main ModSecurity
directives/settings is available at source code archive, labeled as
*modsecurity.conf-recommended*. It is also available at [our git
repository](https://raw.github.com/SpiderLabs/ModSecurity/master/modsecurity.conf-recommended).
These items listed on this recommended configuration are the items that
the Admin should handle and configure for their own site. These settings
should not be including within 3rd party rules files.

## Impedance Mismatch {#impedance_mismatch}

Web application firewalls have a difficult job trying to make sense of
data that passes by, without any knowledge of the application and its
business logic. The protection they provide comes from having an
independent layer of security on the outside. Because data validation is
done twice, security can be increased without having to touch the
application. In some cases, however, the fact that everything is done
twice brings problems. Problems can arise in the areas where the
communication protocols are not well specified, or where either the
device or the application do things that are not in the specification.
In such cases it may be possible to design payload that will be
interpreted in one way by one device and in another by the other device.
This problem is better known as Impedance Mismatch. It can be exploited
to evade the security devices.

While we will continue to enhance ModSecurity to deal with various
evasion techniques the problem can only be minimized, but never solved.
With so many different application backend chances are some will always
do something completely unexpected. The only solution is to be aware of
the technologies in the backend when writing rules, adapting the rules
to remove the mismatch. See the next section for some examples.

### Impedance Mismatch with PHP Apps {#impedance_mismatch_with_php_apps}

1.  When writing rules to protect PHP applications you need to pay
    attention to the following facts:
2.  When \"register_globals\" is set to \"On\" request parameters are
    automatically converted to script variables. In some PHP versions it
    is even possible to override the \$GLOBALS array.
3.  Whitespace at the beginning of parameter names is ignored. (This is
    very dangerous if you are writing rules to target specific named
    variables.)
4.  The remaining whitespace (in parameter names) is converted to
    underscores. The same applies to dots and to a \"\[\" if the
    variable name does not contain a matching closing bracket. (Meaning
    that if you want to exploit a script through a variable that
    contains an underscore in the name you can send a parameter with a
    whitespace or a dot instead.)
5.  Cookies can be treated as request parameters.
6.  The discussion about variable names applies equally to the cookie
    names.
7.  The order in which parameters are taken from the request and the
    environment is EGPCS (environment, GET, POST, Cookies, built-in
    variables). This means that a POST parameter will overwrite the
    parameters transported on the request line (in QUERY_STRING).
8.  When \"magic_quotes_gpc\" is set to \"On\" PHP will use backslash to
    escape the following characters: single quote, double quote,
    backslash, and the nul byte.
9.  If \"magic_quotes_sybase\" is set to \"On\" only the single quote
    will be escaped using another single quote. In this case the
    \"magic_quotes_gpc\" setting becomes irrelevant. The
    \"magic_quotes_sybase\" setting completely overrides the
    \"magic_quotes_gpc\" behaviour but \"magic_quotes_gpc\" still must
    be set to \"On\" for the Sybase-specific quoting to be work.
10. PHP will also automatically create nested arrays for you. For
    example \"p\[x\]\[y\]=1\" results in a total of three variables.
