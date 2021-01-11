for l in google_fct_data:
    print(l)
    
    
out[0]

json.dumps(out[0])
print(json.dumps(out[0], indent = 4))

if output_format not in ['pandas', 'json']:
    raise ValueError('Output format must be either "json" or "pandas" for a pandas df.')
else:
    if output_format == 'json':
        out = json.dumps(out[0])
    else:
        # pd.concat([pd.DataFrame([d]) for d in out[0]])