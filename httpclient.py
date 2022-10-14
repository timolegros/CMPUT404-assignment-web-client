#!/usr/bin/env python3
# coding: utf-8
# Copyright 2016 Abram Hindle, https://github.com/tywtyw2002, and https://github.com/treedust
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import base64
# Do not use urllib's HTTP GET and POST mechanisms.
# Write your own HTTP GET and POST
# The point is to understand what you have to send and get experience with it

import sys
import socket
import re
# you may use urllib to encode data appropriately
import urllib.parse


def help():
    print("httpclient.py [GET/POST] [URL]\n")


class HTTPResponse(object):
    def __init__(self, code=200, body=""):
        self.code = code
        self.body = body


def get_host_port(url, protocol):
    """
    Given a url this function extracts the host, port, and determines whether the url contained an ip e.g. 127.0.0.1:80
    :param url: A url that DOES NOT include the protocol e.g. www.google.com NOT http://www.google.com
    :param protocol: 'http' or 'https'
    :return: (host, port, is_ip) If the port is not defined we assume 80 or 443 for http and https respectively.
    """
    combined = url.split("/")[0]
    tempList = combined.split(":")
    if len(tempList) == 1:
        # return just the host
        if protocol == 'http':
            return tempList[0], 80, False
        elif protocol == 'https':
            return tempList[0], 443, False
    if len(tempList) == 2:
        return tempList[0], int(tempList[1]), True


def get_base_url(url):
    return url.split("/")[0]


def get_path(url, protocol):
    """
    Given a url this function will return the path of the url e.g. '/something/test' if url is 'www.google.com/something/test'
    :param url: A url that DOES NOT include the protocol e.g. www.google.com NOT http://www.google.com
    :param protocol: 'http' or 'https'
    :return: The path of the url
    """
    (host, slash, path) = url.partition("/")
    # DO NOT USE slash instead of "/" since the above returns '' for slash and path if url is like 'www.google.com'
    # thus the below code returns "/" if that is the case
    return "/" + path


def get_protocol_url(full_url):
    if full_url.startswith("https:"):
        return "https", full_url.partition("https://")[-1]
    elif full_url.startswith("http:"):
        return "http", full_url.partition("http://")[-1]
    else:
        # default to http
        return "http", full_url


def get_remote_ip(host):
    print(f'Getting IP for {host}')
    try:
        remote_ip = socket.gethostbyname(host)
    except socket.gaierror:
        print('Hostname could not be resolved. Exiting')
        sys.exit()

    print(f'Ip address of {host} is {remote_ip}')
    return remote_ip


def is_binary_data(data):
    set_data = set(data)
    if set_data == {'0', '1'} or set_data == {'1'} or set_data == {'0'}:
        return True
    else:
        return False


class HTTPClient(object):
    # def get_host_port(self,url):

    def connect(self, host, port):
        print(f"Attempting to connect to {host} on port {port}")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        print(f"Connected to {host} on port {port}")
        return None

    def get_code(self, data):
        return None

    def get_headers(self, data):
        return data.split("\r\n\r\n")[0]

    def get_body(self, data):
        return data.split("\r\n\r\n")[1]

    def sendall(self, data):
        self.socket.sendall(data.encode('utf-8'))

    def close(self):
        self.socket.close()

    # read everything from the socket
    def recvall(self, sock):
        buffer = bytearray()
        done = False
        while not done:
            part = sock.recv(1024)
            if part:
                buffer.extend(part)
            else:
                done = not done
        return buffer.decode('utf-8')

    def GET(self, url, args=None):
        [protocol, short_url] = get_protocol_url(url)
        [host, port, is_ip] = get_host_port(short_url, protocol)

        address = host
        if not is_ip:
            address = get_remote_ip(host)

        path = get_path(short_url, protocol)

        # at this point we have the protocol, ip, port, and path extracted from the url, so we are ready to request

        payload = f'GET {path} HTTP/1.1\r\nHost: {get_base_url(short_url)}\r\nUser-Agent: python/3\r\nAccept: */*\r\nConnection: close\r\n\r\n'

        self.connect(address, port)

        print("Request:\n", payload, sep="")
        self.sendall(payload)

        response = self.recvall(self.socket)
        self.close()
        print("Response:\n", response, sep="")

        header_lines = response.replace('\r', '').split('\n')
        protocol = header_lines[0].split(' ')[0]
        status_code = header_lines[0].split(' ')[1]
        status_msg = header_lines[0].partition(status_code)[-1].strip()
        body = response.split("\r\n\r\n")[1]

        return HTTPResponse(int(status_code), body)

    def POST(self, url, args=None):
        [protocol, short_url] = get_protocol_url(url)
        [host, port, is_ip] = get_host_port(short_url, protocol)

        address = host
        if not is_ip:
            address = get_remote_ip(host)

        path = get_path(short_url, protocol)

        req_body = ''
        count = 1

        if args:
            for id, data in args.items():
                key = id
                value = data

                # if the key is in binary then convert to base64
                if is_binary_data(key):
                    key = base64.b64encode(key.encode('ascii'))

                # if the value is in binary then convert to base64
                if is_binary_data(value):
                    value = base64.b64encode(value.encode('ascii'))

                req_body += f"{key}={value}"
                if count != len(args):
                    req_body += '&'
                count += 1

        # url encoding
        req_body = req_body.replace("%20", " ").replace("%21", "!").replace("%22", '"').replace("%23", "#")\
            .replace("%24", "$").replace("%25", "%").replace("%26", "&").replace("%27", "'").replace("%28", "(")\
            .replace("%29", ")").replace("%2B", " ")

        if req_body != '':
            payload = f"POST {path} HTTP/1.1\r\nHost: {get_base_url(short_url)}\r\nAccept: */*\r\nContent-Length: {len(req_body.encode('utf-8'))}\r\nContent-Type: application/x-www-form-urlencoded\r\nConnection: close\r\n\r\n{req_body}\r\n\r\n"
        else:
            payload = f"POST {path} HTTP/1.1\r\nHost: {get_base_url(short_url)}\r\nAccept: */*\r\nContent-Length: {len(req_body.encode('utf-8'))}\r\nContent-Type: application/x-www-form-urlencoded\r\nConnection: close\r\n\r\n"

        self.connect(address, port)

        print("Request:\n", payload, sep="")
        self.sendall(payload)

        response = self.recvall(self.socket)
        self.close()
        print("Response:\n", response, sep="")
        print("\n")

        header_lines = response.replace('\r', '').split('\n')
        protocol = header_lines[0].split(' ')[0]
        status_code = header_lines[0].split(' ')[1]
        status_msg = header_lines[0].partition(status_code)[-1].strip()
        body = response.split("\r\n\r\n")[1]

        return HTTPResponse(int(status_code), body)

    def command(self, url, command="GET", args=None):
        if (command == "POST"):
            return self.POST(url, args)
        else:
            return self.GET(url, args)


if __name__ == "__main__":
    client = HTTPClient()
    command = "GET"
    print(len(sys.argv), sys.argv)
    if (len(sys.argv) <= 1):
        help()
        sys.exit(1)
    elif (len(sys.argv) == 3):
        print(client.command(sys.argv[2], sys.argv[1]))
    else:
        print(client.command(sys.argv[1]))
