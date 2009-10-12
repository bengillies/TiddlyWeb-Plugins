from BeautifulSoup import BeautifulSoup

def shorten(mystr, count):
    shortened_str = mystr[0:count]
    soup = BeautifulSoup(shortened_str)
    return soup.prettify()