from urllib import parse


urn_list = ("urn:btih:", "urn:ed2k:", "urn:bitprint:", "urn:tree:tiger:", "urn:sha1:", "urn:md5:")

def ParseMagnetLink(magnet_link):
    assert type(magnet_link) is str, "magnet_link is not str"
    assert len(magnet_link) is not 0, "magnet_link is empty"

    assert magnet_link[0:8] == "magnet:?", \
        "magnet_link seems to invalid. Link does not start with 'magnet:?'"

    magnet_details = {
        'xt' : None,
        'dn' : None,
        'tr' : set(),
        'xs': set(),
    }

    details = magnet_link.replace('magnet:?', '')
    for magnet_property in details.split('&'):
        if magnet_property[0:3] == 'xt=':
            if magnet_details['xt']:
                print("'xt' field already defined. Magnet link has more than one 'xt' property. Ignoring.")
                continue
            magnet_property = magnet_property.replace('xt=', '')
            for urn in urn_list:
                if urn in magnet_property:
                    hash = magnet_property.replace(urn, "")
                    magnet_details['xt'] = (urn, hash.upper())

        elif magnet_property[0:3] == 'dn=':
            if magnet_details['dn']:
                print("'dn' field already defined. Magnet link has more than one 'dn' property. Ignoring.")
                continue
            magnet_details['dn'] = magnet_property.replace('dn=', '')

        elif magnet_property[0:3] in ('tr=', 'xs='):
            field = magnet_property[0:3]
            magnet_details[field.replace("=", "")].add(magnet_property.replace(field, ''))

        else:
            print("Magnet Property not supported: {:s}".format(magnet_property))

    return(magnet_details)


def MergeMagnetLinks(new_magnet_name, magnet_link_list):
    assert type(new_magnet_name) is str, "magnet_link is not str"
    assert len(new_magnet_name) is not 0, "new_magnet_name is empty"

    assert not sum((magnet_link[0:8] != "magnet:?" for magnet_link in magnet_link_list)), \
        "magnet_link_list seems to contain invalid magnet links. Links which do not start with 'magnet:?'"

    xt = None
    tr = set()
    for magnet_link in magnet_link_list:

        magnet_details = ParseMagnetLink(parse.unquote(magnet_link.replace("&amp;", "&")))
        for detail in magnet_details:
            if detail == 'xt':
                if xt is None:
                    xt = magnet_details['xt']
                else:
                    if xt != magnet_details['xt']:
                        raise Exception("magnet_links contain different hashes.")
                    continue
            if detail == "tr":
                for tracker in magnet_details['tr']:
                    tr.add(tracker)

    new_magnet_link = "&".join(["".join(('xt=', xt[0], xt[1])), "".join(('dn=', new_magnet_name.replace(" ", "_")))] + list("".join(('tr=', parse.quote(tracker))) for tracker in tr))
    new_magnet_link = "".join(("magnet:?", new_magnet_link))
    return(new_magnet_link)








if __name__ == '__main__':
    magnet_links = ("magnet:?xt=urn:btih:AE4CF1D187E9484A07114C1B720FA456E47B8590&" \
                  "dn=%5Bmonova.org%5D+Marilyn+Manson+-+Discography+%281994+-+2009%29+%5BFLAC%5D+%5Bh33t%5D+-+Kitlope&" \
                  "tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&" \
                  "tr=udp%3A%2F%2Fopen.demonii.com%3A1337&" \
                  "tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&" \
                  "tr=udp%3A%2F%2Fexodus.desync.com%3A6969",
                  "magnet:?xt=urn:btih:ae4cf1d187e9484a07114c1b720fa456e47b8590&"
                  "dn=Marilyn+Manson+-+Discography+%281994+-+2009%29+%5BFLAC%5D+-+Kitlope&"
                  "tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Fzer0day.ch%3A1337&"
                  "tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&"
                  "tr=udp%3A%2F%2Fpublic.popcorn-tracker.org%3A6969",
                   )

    merged_magnets = MergeMagnetLinks("New Magnet Link", magnet_links)
    print(merged_magnets)
