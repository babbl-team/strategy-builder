import datetime
import math
import os
import pytz

GOOFY_ASCII = """
 __    __              __                                          __                          __ 
/  |  /  |            /  |                                        /  |                        /  |
$$ |  $$ |  ______   _$$ |_     ______    ______   _______    ____$$ |  _______       ______  $$/ 
$$ |  $$ | /      \ / $$   |   /      \  /      \ /       \  /    $$ | /       |     /      \ /  |
$$ |  $$ |/$$$$$$  |$$$$$$/   /$$$$$$  |/$$$$$$  |$$$$$$$  |/$$$$$$$ |/$$$$$$$/      $$$$$$  |$$ |
$$ |  $$ |$$ |  $$ |  $$ | __ $$ |  $$/ $$    $$ |$$ |  $$ |$$ |  $$ |$$      \      /    $$ |$$ |
$$ \__$$ |$$ |__$$ |  $$ |/  |$$ |      $$$$$$$$/ $$ |  $$ |$$ \__$$ | $$$$$$  | __ /$$$$$$$ |$$ |
$$    $$/ $$    $$/   $$  $$/ $$ |      $$       |$$ |  $$ |$$    $$ |/     $$/ /  |$$    $$ |$$ |
 $$$$$$/  $$$$$$$/     $$$$/  $$/        $$$$$$$/ $$/   $$/  $$$$$$$/ $$$$$$$/  $$/  $$$$$$$/ $$/ 
          $$ |                                                                                    
          $$ |                                                                                    
          $$/                                                                                     
                            ---- [ UPTRENDS.AI Base Utilities ] ----
"""

def truncate_fill_str(s: str, length: int=15, ellipses: str="...") -> str:
    # Truncates a string to len, adds ... if necessary,
    # and fills spaces to the right with spaces
    s = s.replace("\n", " ")
    if len(s) > length:
        return s[:length] + ellipses
    return s + " " * ((length - len(s))+len(ellipses))

def curr_time_factory():
    return datetime.datetime.now(pytz.utc)

def print_success(print_str: str):
    # Prints the passed-in string in green
    print(f"\033[92m\033[1m{print_str}\033[0m")

def print_failure(print_str: str):
    # Prints the passed-in string in red
    print(f"\033[91m\033[1m{print_str}\033[0m")

def print_warning(print_str: str):
    # Prints the passed-in string in yellow
    print(f"\033[93m\033[1m{print_str}\033[0m")

def print_info(print_str: str):
    # Prints the passed-in string in blue and in bold
    print(f"\033[96m\033[1m{print_str}\033[0m")

def print_bold(print_str: str):
    # Prints the passed-in string in bold
    print(f"\033[1m{print_str}\033[0m")


def percent_change_fmt(num: float) -> str:
    """Takes a decimal or ratio, will multiply by 100 and return 
    a string with a % sign, or $$x if > 2.0
    """
    if abs(num) > 2:
        sign_str = "+" if num > 0 else "-"
        return f"{sign_str}{round(abs(num), 1)}x"
    if num > 1:
        return f"+{round(num*100)}%"
    if num > 0:
        return f"+{round(num * 100, 1)}%"
    else:
        return f"{round(num * 100, 1)}%"

def format_time(ts: float):
    """
    Takes time in seconds, and returns a ms int string if time < 2s, 
    a min:sec string if time > 120s, and
    otherwise returns seconds string to 1 decimal
    """
    if ts is None:
        return "n/a"
    if ts < 1:
        return "{}ms".format(int(ts * 1000))
    if ts > 120:
        return "{}m {}s".format(int(ts // 60), int(ts % 60))
    else:
        return "{:.1f}s".format(ts)
    

def highlight_kwd_in_str(kwd: str, search_str: str, max_width: int=None, ellipses: str="...", print_match_str:bool=True) -> str:
    # Highlights the keyword in the search string, and returns the result
    # if num_chars_around is None, then we'll default to final string using the full terminal width
    kwd = kwd.lower()
    search_str = search_str.replace("\n", " ")
    kwd_idx = search_str.lower().find(kwd)
    if kwd_idx == -1:
        # Not found
        return None
    terminal_width = os.get_terminal_size().columns if max_width is None else max_width
    num_chars_around = (terminal_width - len(kwd)) // 2

    # these are the full output string start & end indexes
    pre_str = search_str[:kwd_idx]
    end_str = search_str[kwd_idx + len(kwd):]
    pre_chars_around = num_chars_around 
    end_chars_around = num_chars_around 

    if len(pre_str)+len(ellipses) > pre_chars_around:
        # overwriting the first len(ellipses) characters with the ellipses
        pre_str = pre_str[-pre_chars_around:]
        pre_str = ellipses + pre_str[len(ellipses):]
    else:
        # This means we add spaces to the start
        pre_str = " " * (pre_chars_around - len(pre_str)) + pre_str

    if len(end_str) > end_chars_around:
        # overwriting the last len(ellipses) characters with the ellipses
        end_str = end_str[:end_chars_around]
        end_str = end_str[:-len(ellipses)] + ellipses
    else:
        # This means we add spaces to the end
        end_str = end_str + " " * (end_chars_around - len(end_str))

    # wrap kwd in bold and underline ANSI codes
    kwd_match_str = f"\033[96m\033[1m{kwd.upper()}\033[0m"
    # write our match string with the ANSI code out to system out directly
    if print_match_str:
        print(pre_str + kwd_match_str + end_str)
    match_str = pre_str + kwd_match_str + end_str
    return match_str

def sizeof_fmt(num, suffix='b', magnitude: int = None) -> str:
    if magnitude is None:
        magnitude = int(math.floor(math.log(num, 1000)))

    val = num / math.pow(1000, magnitude)
    if magnitude > 7:
        return '{:.1f}{}{}'.format(val, 'Y', suffix)
    return '{:3.1f}{}{}'.format(val, ['', 'k', 'm', 'g', 't', 'Pi', 'Ei', 'Zi'][magnitude], suffix)


if __name__=="__main__":
    print_success(GOOFY_ASCII)
    print_info("This module contains a collection of utility functions and classes, some examples...")
    print_info("1. color printing functions")
    print_info("   > print_info(txt)")
    print_success("   > print_success(txt)")
    print_warning("   > print_warning(txt)")
    print_failure("   > print_failure(txt)")
    print()
    print_info("2. some string functions...")
    print_bold("   > truncate_fill_str(s: str, length: int=15, ellipses: str='...') -> str")
    print_bold("      - Truncates a string to len, adds an elipses if you want, and fills the rest with spaces to make sure any str you pass in comes back the same length")
    print_bold("\n   > highlight_kwd_in_str(kwd: str, search_str: str, num_chars_around: int=None, ellipses: str='...', print_match_str:bool=True) -> str")
    print_bold("      - Finds the first keyword match, and prints it centered in the console")
    test_str = "This is a test string to search for maybe the keywords key or words or string or something else who knows"
    long_str = test_str * 5 + " finds me " + test_str * 5
    long_str2 = test_str * 5 + " in the " + test_str * 5
    long_str3 = test_str * 5 + " search strings " + test_str * 5
    highlight_kwd_in_str("finds me", long_str, max_width=100)
    highlight_kwd_in_str("in the", long_str2, max_width=100)
    highlight_kwd_in_str("search strings", long_str3, max_width=100)

    print()
    print_info("3. some number formatting functions...")
    print_bold("   > percent_change_fmt(num: float) -> str")
    print_bold("      - Takes a decimal ratio (e.g. 0.5, 2.1), will multiply by 100 and return a string with a % sign, or ##x if > 2.0")
    print_bold(f"      - e.g. percent_change_fmt(0.5) ----> {percent_change_fmt(0.5)}")
    print_bold(f"      - e.g. percent_change_fmt(2.1) ----> {percent_change_fmt(2.1)}")
    print_bold(f"      - e.g. percent_change_fmt(-5.1) ---> {percent_change_fmt(-5.1)}")
    print_bold("   > format_time(ts: float) -> str")
    print_bold("      - Takes time in seconds, and returns a ms int string if time < 2s, a min:sec string if time > 120s, and otherwise returns seconds string to 1 decimal")
    print_bold(f"      - e.g. format_time(0.5) ---> {format_time(0.5)}")
    print_bold(f"      - e.g. format_time(115) ---> {format_time(115)}")
    print_bold(f"      - e.g. format_time(425) ---> {format_time(425)}")
    