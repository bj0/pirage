# pirage
Raspberry Pi Garage Controller

## TODO

note: rpi.gpio might fail to build with pip without CFLAGS="-fcommon"

### Create Self-Signed Certs

from: http://nategood.com/client-side-certificate-authentication-in-ngi
& https://gist.github.com/mtigas/952344

We need some certs and keys to authenticate the client to the server. 

Create the CA Key and Certificate for signing Client Certs (-des3 encrypts keyfile with a passphrase):
 
    openssl genrsa -aes256 -passout pass:xxxx -out ca.pass.key 4096
    openssl rsa -passin pass:xxxx -in ca.pass.key -out ca.key
    rm ca.pass.key

//    openssl genrsa [-des3] -out ca.key 4096
//    openssl req -new -x509 -days 365 -key ca.key -out ca.crt

Create the Server Key, CSR, and Certificate:

    openssl genrsa -aes256 -passout pass:xxxx -out server.pass.key 4096
    openssl rsa -passin pass:xxxx -in server.pass.key -out server.key
    rm server.pass.key

//    openssl genrsa [-des3] -out server.key 1024
//    openssl req -new -key server.key -out server.csr

We're self signing our own server cert here.  This is a no-no in production:

    openssl req -new -key server.key -out server.csr
    openssl x509 -req -days 3650 -in server.csr -CA ca.pem -CAkey ca.key -set_serial 01 -out server.pem

//    openssl x509 -req -days 365 -in server.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out server.crt

Create the Client Key and CSR:

    openssl genrsa -aes256 -passout pass:xxxx -out client.pass.key 4096
    openssl rsa -passin pass:xxxx -in client.pass.key -out client.key
    rm client.pass.key

//    openssl genrsa [-des3] -out client.key 1024
//    openssl req -new -key client.key -out client.csr

Sign the client certificate with our CA cert.  Unlike signing our own server cert, this is what we want to do:

    openssl req -new -key client.key -out client.csr
    openssl x509 -req -days 3650 -in client.csr -CA ca.pem -CAkey ca.key -set_serial 01 -out client.pem

//    openssl x509 -req -days 365 -in client.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out client.crt

Test server:

    curl -v -s -k --key client.key --cert client.crt https://example.com


#### Generate KeyStore

For Android (java) we need a keystore.  We can create a pkcs12 keystore with:

    openssl pkcs12 -export -in client.crt -inkey client.key -chain -CAfile ca.crt -name "tangled.superstring.org" -out client.p12

or

    openssl pkcs12 -export -clcerts -in client.crt -inkey client.key -out client.p12
    
**NOTE:** So far I haven't figured out how to get Android 8.x to accept the self created CA, but if you point it directly at the self-signed server cert, it accepts it.  The new Network Security config makes this simple