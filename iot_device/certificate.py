#!/usr/bin/env python3

from OpenSSL import crypto
from socket import gethostname

def create_key_cert_pair():
    # private key
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 1024)

    # signed certificate
    cert = crypto.X509()
    cert.get_subject().C  = "US"
    cert.get_subject().ST = "CA"
    cert.get_subject().L  = "Berkeley"
    cert.get_subject().O  = "IoT 49"
    cert.get_subject().OU = "IoT Python"
    cert.get_subject().CN = gethostname()
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10*365*24*60*60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha1')

    return (
        crypto.dump_privatekey(crypto.FILETYPE_PEM, key),
        crypto.dump_certificate(crypto.FILETYPE_PEM, cert))


##########################################################################
# Example

def main():
    key, cert = create_key_cert_pair()
    print(key.decode())
    print(cert.decode())

if __name__ == "__main__":
    main()
