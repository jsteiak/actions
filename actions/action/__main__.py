'''
Created on Dec 8, 2020

@author: istiakog
'''
from json import loads
from os import getenv

if __name__ == '__main__':
    print('Hello from python')
    print(getenv('GITHUB_TOKEN'))
    print(getenv('GITHUB_CONTEXT'))
    context = loads(getenv('GITHUB_CONTEXT'))
    for k, v in context.items():
        print(f"{k}:{v}")
