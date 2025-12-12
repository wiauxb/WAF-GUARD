"""
Macro Call Trace Tool

Tool to trace macro calls and their definitions in the WAF configuration.
"""

from langchain_core.tools import tool


@tool
def get_macro_call_trace(node_id: int) -> str:
    """
    Get the macro call trace of a node based on its ID.

    This tool retrieves the complete macro call stack, showing where a macro
    is called and how it's defined, including nested macro calls.

    Args:
        node_id (int): The ID of the node to get the macro call trace

    Returns:
        str: Formatted string showing the macro call trace with line numbers and content

    Example:
        >>> get_macro_call_trace(node_id=12345)
        '''
        Macro call trace for node 12345, EnableSSL:

        Line 156: /etc/apache2/sites-enabled/example.conf
        Use <Macro EnableSSL $domain>
            SSLEngine on
            SSLCertificateFile /etc/ssl/certs/${domain}.crt
            SSLCertificateKeyFile /etc/ssl/private/${domain}.key
        </Macro>

        Line 42: /etc/apache2/macros/ssl-config.conf
        <Macro EnableSSL $domain>
            SSLEngine on
            SSLCertificateFile /etc/ssl/certs/${domain}.crt
            SSLCertificateKeyFile /etc/ssl/private/${domain}.key
            SSLProtocol all -SSLv2 -SSLv3
            SSLCipherSuite HIGH:!aNULL:!MD5
        </Macro>
        '''
    """
    # DUMMY IMPLEMENTATION - Backend services not ready yet
    # Will be replaced with actual AnalysisService integration

    # Generate a realistic macro trace output
    output = f"""Macro call trace for node {node_id}, EnableSSL:

Line 156: /etc/apache2/sites-enabled/example.conf
Use EnableSSL example.com

<Macro EnableSSL $domain>
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/${{domain}}.crt
    SSLCertificateKeyFile /etc/ssl/private/${{domain}}.key

    # Call nested security macro
    Use SecureSSLConfig
</Macro>

Line 42: /etc/apache2/macros/ssl-config.conf
<Macro EnableSSL $domain>
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/${{domain}}.crt
    SSLCertificateKeyFile /etc/ssl/private/${{domain}}.key

    # Enhanced SSL configuration
    SSLProtocol all -SSLv2 -SSLv3 -TLSv1 -TLSv1.1
    SSLCipherSuite ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256
    SSLHonorCipherOrder on

    # HSTS configuration
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"

    # Call nested security macro
    Use SecureSSLConfig
</Macro>

Line 18: /etc/apache2/macros/security-headers.conf
<Macro SecureSSLConfig>
    # OCSP Stapling
    SSLUseStapling on
    SSLStaplingCache "shmcb:logs/stapling-cache(150000)"

    # Security headers
    Header always set X-Frame-Options "DENY"
    Header always set X-Content-Type-Options "nosniff"
</Macro>

[DUMMY DATA] - Backend services not ready yet. This is a mock macro trace.
"""

    return output
