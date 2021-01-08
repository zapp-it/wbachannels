#!/usr/bin/python3

import argparse
import configparser
import errno
import gzip
import os
import socket
import struct
import urllib.parse

from lxml import etree
from urllib.error import HTTPError
from urllib.request import urlretrieve

def _downloadimages(channellogo):
  """
  Download the WBA channels images.
  """
  try:
    channellogodownloadname = urllib.parse.quote(str(channellogo))
    image_url = urllib.parse.urljoin(imagedownloadurl, channellogodownloadname)
    
    urlretrieve(image_url, imagesdownloaddirectory + channellogo)
  except (FileNotFoundError, HTTPError) as err:
    print("Error while trying to download the image %s, the error is %s.\n" % (channellogo, err))
    #print("\n")

def _getchannels(channelstree):
  """
  Gets the WBA channels information.
  """
  if channelstree != None:
    try:
      nodes = channelstree.findall(wbachannelslisttree)
      
      if verbose:
        print("The total number of the channels is %s.\n" % len(nodes))

      root = etree.Element("channels", {"generator-info-name": "wbachannels"})

      for node in nodes:
        # CallLetters
        # ChannelID - Needed for the WBA EPG data ID.
        # ChannelLogo
        # ChannelStreams
        # DisplayChannelName
        # IP
        # PortNumber
        # MTP
        # nPLTVEnabled
        # nPLTVAssetName
        
        channelcallletters = None
        channelid = None
        channellogo = None
        channelname = None
        channelnumber = None

        channelcallletters = node.find("CallLetters")
        if channelcallletters is not None and node.find("CallLetters").text:
          channelcallletters = node.find("CallLetters").text        
        
        channelid = node.find("ChannelID")
        if channelid is not None and node.find("ChannelID").text:
          channelid = node.find("ChannelID").text
        else:
          channelid = None
                  
        channellogo = node.find("ChannelLogo")
        if channellogo is not None and node.find("ChannelLogo").text:
          channellogo = node.find("ChannelLogo").text
          
          # First download the image.
          _downloadimages(channellogo)
          
          # Create the image path.
          channellogo = imagesdownloaddirectory + channellogo
        else:
          channellogo = None
        
        channelname = node.find("DisplayChannelName")
        if channelname is not None and node.find("DisplayChannelName").text:
          channelname = node.find("DisplayChannelName").text
        else:
          channelname = None
          
        channelnumber = node.find("DisplayChannelNumber")
        if channelnumber is not None and node.find("DisplayChannelNumber").text:
          channelnumber = node.find("DisplayChannelNumber").text
        else:
          channelnumber = None
          
        channelstreams = node.find(".//ChannelStreams")
        if channelstreams is not None:
        
          for channelstream in channelstreams:
            channelinformation = etree.SubElement(root, "channel", lang="nl") 
            
            # First get the information for the channel type, needed for the channel name.
            if channelstream.find("MTP").attrib["ExternalID"] is not None:
              channeltype = channelstream.find("MTP").attrib["ExternalID"]
            
            if channeltype in qualityconfigitems:
              extension = qualityconfigitems[channeltype]
              enabled = "true"
            else:
              extension = ""
              enabled = "false"
                            
            if len(extension) > 0:
              if extension not in channelname:
                newchannelname = channelname + " " + extension
              else:
                newchannelname = channelname
            else:
              newchannelname = channelname

            etree.SubElement(channelinformation, "name").text = newchannelname
            etree.SubElement(channelinformation, "number").text = channelnumber
            etree.SubElement(channelinformation, "image").text = channellogo

            channelip = channelstream.find("IP")
            if channelip is not None and channelstream.find("IP").text:  
              channelip = channelstream.find("IP").text
            else:
              channelip = None
          
            channelportnumber = channelstream.find("PortNumber")
            if channelportnumber is not None and channelstream.find("PortNumber").text:
              channelportnumber = channelstream.find("PortNumber").text
            else:
              channelportnumber = None
            
            if channelip and channelportnumber:
              channelurl = "rtp://@" + channelip + ":" + channelportnumber
            else:
              channelurl = None
              
            etree.SubElement(channelinformation, "url").text = channelurl

            channelreplaytvenabled = channelstream.find("nPLTVEnabled")
            if channelreplaytvenabled is not None and channelstream.find("nPLTVEnabled").text:
              channelreplaytvenabled = channelstream.find("nPLTVEnabled").text

              if channelreplaytvenabled.lower() == "true":
                channelreplaytvenabled = True
              
              else:
                channelreplaytvenabled = False
           
              if channelreplaytvenabled:
              
                if channelstream.find("nPLTVAssetName") is not None:
                  channelreplayurl = urllib.parse.urljoin(replaytvurl, channelstream.find("nPLTVAssetName").text)
            
                  etree.SubElement(channelinformation, "replayurl").text = channelreplayurl
            
            etree.SubElement(channelinformation, "enabled").text = enabled
            etree.SubElement(channelinformation, "wbaepgid").text = channelid
            etree.SubElement(channelinformation, "callletters").text = channelcallletters
        
      if verbose:  
        print(etree.tostring(root, encoding = "UTF-8", pretty_print = True).decode())
      
      try:
        with open(channelsxmlfilenametosave, "wb") as channelsfile:
          channelsfile.write(str.encode('<?xml version="1.0" encoding="utf-8"?>\n'))
          channelsfile.write(str.encode(etree.tostring(root, encoding = "UTF-8", pretty_print = True).decode()))
          channelsfile.close()

      except IOError as err:
        print("Can not create the %s file, the error is %s.\n" % (channelsxmlfilenametosave, err))
        
    except (etree.XMLSyntaxError, etree.ParserError) as err:
      print(err)
      print("Could not read the channels information from the %s file, the error is %s.\n" % (channelsrawfilenametosave, err))
      return 1

def main():
  """
  Defines the central entrypoint for this module.
  :param name: -d, --dry, Dry mode, use the specified local file instead of using MC.
  :param name: -v, --verbose, Verbose mode.
  """
  if dryrun:
    try:
      raw = open(dryrun, encoding="utf8").read()
      
    except IOError as err:
      print("The dryrun file %s does not exists, the error is %s.\n" % (dryrun, err))
      return 1
    
  else:
    try:
      raw = _receive()
     
    except:
      print("No WBA channels MC data received.\n")
      return 1
       
  if raw:  
    if not os.path.exists(os.path.dirname(channelsrawfilenametosave)):
      try:
        os.makedirs(os.path.dirname(channelsrawfilenametosave))
      except OSError as err: # Guard against race condition.
        if err.errno != errno.EEXIST:
          print("Cannot create the directory %s, the error is %s.\n" % (os.makedirs(os.path.dirname(channelsrawfilenametosave)), err))
          return 1

    if not os.path.exists(os.path.dirname(imagesdownloaddirectory)):
      try:
        os.makedirs(os.path.dirname(imagesdownloaddirectory))
      except OSError as err: # Guard against race condition.
        if err.errno != errno.EEXIST:
          print("Cannot create the directory %s, the error is %s.\n" % (os.makedirs(os.path.dirname(imagesdownloaddirectory)), err))
          return 1
  
    parser = etree.XMLParser(strip_cdata = False)
    
    try:
      oldfile = open(channelsrawfilenametosave, encoding="utf8").read()
      oldfileroot = etree.ElementTree(etree.fromstring(oldfile, parser)).getroot()
      oldversion = oldfileroot.attrib["version"]
      
      if verbose:
        print("The old document version is %s.\n" % oldversion)
      
    except IOError:
      # The wbachannels.xml file does not exists.
      oldversion = 0
      
      if verbose:
        print("The old %s file does not exists.\n" % channelsrawfilenametosave)
    
    channelstree = etree.ElementTree(etree.fromstring(raw, parser))
    channelsroot = channelstree.getroot()
    channelsversion = channelsroot.attrib["version"]

    if verbose:
      print("The new document version is %s.\n" % channelsversion)
  
    if channelsversion != oldversion:
      try:
        channelsfile = open(channelsrawfilenametosave, "wb")
        channelsfile.write(raw)
        channelsfile.close()
      except IOError as err:
        # Can not create the wbachannelsfile.xml file.
        print("Can not create the %s file, the error is %s.\n" % (channelsrawfilenametosave, err))
        return 1
      
      if verbose:
        print("Written the new %s file.\n" % channelsrawfilenametosave)
      
      _getchannels(channelstree)
  
  return 0

def _receive():
  """
  Receive the WBA channels configuration from MC.
  """
  try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", int(serverport)))
    mreq = struct.pack("4sl", socket.inet_aton(serveraddress), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    packetdictonary = {}

    while True:
      # Get the packet numbers.
      packet = bytearray(sock.recv(int(packetsize)))

      packetid = int.from_bytes(packet[4:8], byteorder="big")

      if verbose:
        print("The MC receive packet number is:", packetid)

      if packetid in list(packetdictonary):
        # Sort the packet(s).
        sort = sorted(packetdictonary)
        if verbose:
          print("The total packets received is.\n", len(packetdictonary))

        dictonary = bytearray() 
        
        for i in range(1, len(sort) + 1):
          dictonary.extend(packetdictonary[i])

        raw = _unzip(dictonary)
        return raw
      else:
        packetdictonary[packetid] = packet[8:]

  except socket.timeout:
    print("Timeout while connecting to %s.\n" % serveraddress)
    return 1

  except socket.error as err:
    print("A socket error occured, the error is %s.\n" % err)
    return 1

  finally:
    if sock != None:
      sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, socket.inet_aton(serveraddress) + socket.inet_aton("0.0.0.0"))
      sock.close()
      sock = None
 
def _unzip(raw):
  """
  Uzip the raw data from the MC data.
  """
  try:
    data = gzip.decompress(raw)
    return data
  
  except OSError as err:
    print("The MC data is not a gzip file, the error is %s.\n" % err)
    return 1

if __name__ == "__main__":
  """
  Define the central entrypoint for this module.
  """
  arguments = argparse.ArgumentParser()
  arguments.add_argument("-d", "--dry", help = "Dry mode, use the specified local file instead of using MC.", type = str, dest = "dry", default = None)
  arguments.add_argument("-v", "--verbose", help = "Verbose mode.", type = bool, dest = "verbose", default = False)

  options = arguments.parse_args()

  config = configparser.ConfigParser(allow_no_value = True)

  # Don't use the lowercase option of the ConfigParser.
  config.optionxform = str
  try:
    with open("wbachannels.conf") as f:
      config.read_file(f)
      f.close()

    # Multicast channel configuration.
    packetsize = config["multicast channel configuration"]["packetsize"]
    serveraddress = config["multicast channel configuration"]["serveraddress"]
    serverport = config["multicast channel configuration"]["serverport"]

    # Common configuration.
    directorytosavefiles = config["common"]["directorytosavefiles"]
    
    # Quality configuration.
    qualityconfigitems = dict(config.items("quality"))

    if directorytosavefiles is "":
      directorytosavefiles = os.path.join(os.path.expanduser("~"), ".wba")
      
    imagedownloadurl = config["common"]["imagedownloadurl"]
    imagesdownloaddirectory = config["common"]["imagesdownloaddirectory"]

    if imagesdownloaddirectory is "":
      imagesdownloaddirectory = os.path.join(os.path.expanduser("~"), directorytosavefiles + "/images/")
    
    replaytvurl = config["common"]["replaytvurl"]

    # The location to save the raw MC xml.
    channelsrawfilenametosave = os.path.join(directorytosavefiles, "wbarawchannels.xml")
    
    # The location to save the channels XML file.
    channelsxmlfilenametosave = os.path.join(directorytosavefiles, "wbachannels.xml")

    # Channels information variables.
    wbachannelslisttree = ".//ChannelList/Channel"
    
    dryrun = options.dry
    verbose = options.verbose

    if not dryrun:
      if verbose:
        print("[multicast channel configuration]")
        print("The receive packet size is %s." % packetsize)
        print("The channel list server address is %s." % serveraddress)
        print("The channel list server port is %s.\n" % serverport)

        print("[common]")
        print("The directory location to save the files is %s." % directorytosavefiles)
        print("The image download URL is %s." % imagedownloadurl)
        print("The replay URL is %s.\n" % replaytvurl)
  
        print("The dry file is %s.\n" % dryrun)
        
  except Exception as err:
    print("The configuration file wbachannels.conf does not exists or could not be found the error is %s." % err)
    exit(1)

  x = main()
  exit(x)  

