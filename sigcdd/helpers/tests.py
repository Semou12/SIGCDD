from django.test import TestCase

# Create your tests here.
def splitsum(L,S):
    result,t = [[]],0
    for n in L:
        r,v,t = (result,[n],n) if t+n>S else (result[-1],n,t+n)
        r.append(v) # append n to last list or [n] to list of lists
    return result


L = [400,250,750,800,125,500,550,100]
print(splitsum(L,1000))

#[[400, 250], [750], [800, 125], [500], [550, 100]]