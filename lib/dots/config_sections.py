"""Static Config List categories; completion must not inspect native sources."""
CATEGORIES = ('all','icons','colors','formatting','apps','files','profile','settings','environment')


def categories(values):
    result=[]
    for value in values:
        value=value.casefold()
        if value not in CATEGORIES:
            raise ValueError('unknown configuration category: '+value+'; choose '+', '.join(CATEGORIES))
        if value not in result:result.append(value)
    return [] if 'all' in result else result
