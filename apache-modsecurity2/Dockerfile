# =============================================================================
# Stage 1: Build ModSecurity v2
# =============================================================================
FROM httpd:2.4 AS modsecurity-build
ARG MODSEC_VERSION=2.9.12

RUN apt-get update && apt-get install -y --no-install-recommends \
    autoconf \
    automake \
    gcc \
    g++ \
    libtool \
    make \
    git \
    libapr1-dev \
    libaprutil1-dev \
    libxml2-dev \
    libyajl-dev \
    libpcre2-dev \
    libcurl4-gnutls-dev \
    pkg-config \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone --depth 1 -b v${MODSEC_VERSION} \
    https://github.com/owasp-modsecurity/ModSecurity.git

WORKDIR /build/ModSecurity
RUN ./autogen.sh && \
    ./configure --with-apxs=/usr/local/apache2/bin/apxs \
                --with-yajl \
                --with-pcre2 && \
    make && \
    make install

# =============================================================================
# Stage 2: Final image
# =============================================================================
FROM httpd:2.4

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libyajl2 \
    libcurl3-gnutls \
    libpcre2-8-0 \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Copy ModSecurity module and unicode.mapping
COPY --from=modsecurity-build /usr/local/apache2/modules/mod_security2.so \
                              /usr/local/apache2/modules/mod_security2.so
COPY --from=modsecurity-build /build/ModSecurity/unicode.mapping \
                              /etc/modsecurity.d/unicode.mapping


COPY bin/* /usr/local/bin/
RUN chmod +x /usr/local/bin/*

# Create necessary directories and user
RUN useradd --system --no-create-home httpd && \
    mkdir -p /etc/modsecurity.d/ \
             /tmp/modsecurity/data \
             /tmp/modsecurity/upload \
             /tmp/modsecurity/tmp \
             /var/log/apache2/ \
             /app

# Setup Python for API (before switching user)
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
RUN pip install --no-cache-dir fastapi uvicorn python-multipart

# Copy API and entrypoint
COPY api/ /app/api/
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set permissions
RUN chown -R httpd:httpd \
        /var/log/apache2 \
        /usr/local/apache2 \
        /etc/modsecurity.d \
        /tmp/modsecurity \
        /app

USER httpd

EXPOSE 8080 9000
ENTRYPOINT ["/entrypoint.sh"]