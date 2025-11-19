FROM rockylinux:9

RUN dnf install -y sudo

COPY scripts /opt/waf_inst
WORKDIR /opt/waf_inst
RUN chmod a+x *.sh && ./install.sh
RUN systemctl disable firewalld

COPY scripts/modules/* /usr/local/lib64/httpd/modules/


# --------------------------------------------
# REST API
# --------------------------------------------

RUN dnf install -y python3 python3-pip
RUN pip3 install fastapi[standard]