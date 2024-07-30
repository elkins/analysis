"""
Print the right-now time in the correct format.
Ready to copy and paste on the header template __date__ field

"""


if __name__ == '__main__':
    import time
    # Print the right-now time in the correct format. Ready to copy and paste on the __date__ field.
    t = time.strftime('%Y-%m-%d %H:%M:%S %z (%a, %B %d, %Y)')
    print('\n==========  date and time for header ========== \n')
    print(f'__date__ = "$Date: {t} $"')
    print('\n===============================================')
    print(f'__dateModified__ = "$Date: {t} $"')
