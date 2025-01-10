#!/bin/env python3

with open('nv_output.txt', 'r') as fp:
    nv_output = fp.read()

print(nv_output)
nv_1 = nv_output.split('=========|')
print(nv_1)
