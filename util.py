import re, math
from collections import Counter

f = open("stopword.txt")
STOP_WORDS = [stopword[0:len(stopword) - 1] for stopword in f.readlines()]

WORD = re.compile(r'\w+')

def get_cosine(vec1, vec2):
     intersection = set(vec1.keys()) & set(vec2.keys())
     numerator = sum([vec1[x] * vec2[x] for x in intersection])

     sum1 = sum([vec1[x]**2 for x in vec1.keys()])
     sum2 = sum([vec2[x]**2 for x in vec2.keys()])
     denominator = math.sqrt(sum1) * math.sqrt(sum2)

     if not denominator:
        return 0.0
     else:
        return float(numerator) / denominator

def text_to_vector(text):
     words = WORD.findall(text)
     c = Counter(words)
     c.subtract(STOP_WORDS)
     return c

def sim(s1, s2):
    v1 = text_to_vector(s1)
    v2 = text_to_vector(s2)
    return get_cosine(v1, v2)

text1 = 'Will there be food?'
text2 = 'Will food be provided?'
text3 = 'Will there be vegetarian food options?'
text4 = 'Can I bring dogs to the event?'

vector1 = text_to_vector(text1)
vector2 = text_to_vector(text2)
vector3 = text_to_vector(text3)
vector4 = text_to_vector(text4)

cosine = get_cosine(vector1, vector2)
cosine2 = get_cosine(vector1, vector3)
cosine3 = get_cosine(vector1, vector4)

print('The similarity between \"{0}\" and \"{1}\" is:{2}'.format(text1, text2, cosine))
print('The similarity between \"{0}\" and \"{1}\" is:{2}'.format(text1, text3, cosine2))
print('The similarity between \"{0}\" and \"{1}\" is:{2}'.format(text1, text4, cosine3))
