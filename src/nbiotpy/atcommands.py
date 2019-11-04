PREFIX = "AT+"
POSTFIX = "\r\n"

RADIO_ON = "CFUN=1"
RADIO_OFF = "c"
REBOOT = "NRB"
GPRS = "CGATT?"
CGAC = "CGACT={}"
SOCR = "NSOCR=\"DGRAM\",17,{},1"
SOCL = "NSOCL={}"
IMEI = "CGSN=1"
IMSI = "CIMI"
CCID = "CCID?"
SOST = "NSOST={}"
SORF = "NSORF={},{}"
CONS = "CSCON?"
SCONN = "CSCON={}"
CGDCS = "CGDCONT={}"
CGDCR = "CGDCONT?"
COPS = "COPS={}"
CGPR = "CGPADDR={}"
COAP = "UCOAP={}"
COAPC = "UCOAPC={}"
NPING = "NPING=\"{}\""
USELCP = "USELCP=1"
CSQ = "CSQ"

MSG_TYPE = "1"

R_OK = "OK"
R_ERROR = "ERROR"

RESPONSE = {
    RADIO_ON: (R_OK, None),
    RADIO_OFF: (R_OK, None),
    REBOOT: ("+UFOTAS", None),
    GPRS: (R_OK, "\+CGATT\:\s+(\d+)"),
    SOCR: (R_OK, "^(\d+)"),
    SOCL: (R_OK, None),
    IMEI: (R_OK, "\+CGSN\:\s+(\d+)"),
    IMSI: (R_OK, "^(\d+)"),
    CCID: (R_OK, "\+CCID\:\s(\d+)"),
    SOST: (R_OK, None),
    SORF: (R_OK, None),
    CONS: (R_OK, None),
    SCONN: (R_OK, None),
    CGDCS: (R_OK, None),
    CGDCR: (R_OK, None),
    COPS: (R_OK, None),
    CGPR: (R_OK, None),
    CGAC: (R_OK, None),
    COAP: (R_OK, None),
    COAPC: (R_OK, None),
    NPING: (R_OK, None),
    USELCP: (R_OK, None),
    CSQ: (R_OK, "\+CSQ\:\s+(\d+),\d+")
}
