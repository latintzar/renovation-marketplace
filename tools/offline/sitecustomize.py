"""Source verification fence: Python tests may connect only to loopback."""
import ipaddress,socket
original=socket.socket.connect
original_ex=socket.socket.connect_ex
original_dns=socket.getaddrinfo
def local(address):
 if isinstance(address,str):return True
 host=address[0]
 if host in ('localhost',''):return True
 try:return ipaddress.ip_address(host).is_loopback
 except ValueError:return False
def connect(self,address):
 if not local(address):raise RuntimeError('External networking is disabled during source verification.')
 return original(self,address)
def connect_ex(self,address):
 if not local(address):raise RuntimeError('External networking is disabled during source verification.')
 return original_ex(self,address)
def dns(host,*args,**kwargs):
 if host is not None and not local((host,0)):raise RuntimeError('External DNS is disabled during source verification.')
 return original_dns(host,*args,**kwargs)
socket.socket.connect=connect;socket.socket.connect_ex=connect_ex;socket.getaddrinfo=dns
