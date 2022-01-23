import requests as B,time as C
from dhooks import Webhook as D
E=D('https://discord.com/api/webhooks/894148879774261288/5rSjlL9VOpEhhTJ89RIxN3T9B2Gex0Rg0huN8NSb8xCVEgur4joyDITJ9JzR_os_7iYX')
while 1:
	A=B.post('https://free.nmadsen.dk/afk',cookies={'connect.sid':'s%3AwOsRxFBPS5JQKRnsQA646xe7DDx1xPJ2.UQy1EO%2FbKQyBUCuwoVnFTtmt0GkGiQferBvChefFeK4'}).text
	if'Not'in A:E.send('<@657629628202090497>');break
	print(A);C.sleep(2.5)