# Function to format numeric numbers as gp cash stacks e.g. 10,0000,000 as 10m
def format_amount(amount):
    if amount >= 1_000_000:
        return f"{amount / 1_000_000:.0f}m" 
    elif amount >= 1_000:
        return f"{amount / 1_000:.0f}k"    
    else:
        return str(amount)                   


# Allows formatted amounts to be parsed in amount altering commands
def parse_amount(amount_str):
    if amount_str[-1].lower() == 'm':
        return int(float(amount_str[:-1]) * 1_000_000)
    elif amount_str[-1].lower() == 'k':
        return int(float(amount_str[:-1]) * 1_000)
    else:
        return int(amount_str)