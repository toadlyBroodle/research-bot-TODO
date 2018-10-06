#! /usr/bin/python3

import sys
import signal
import argparse
import pprint
import json
from time import sleep, localtime, strftime
from datetime import datetime
from random import randint
# Reddit imports:
import praw
import pdb
import re
import os
# Twitter imports:
import tweepy
# Web Scraping, Parsing imports:
import getpass
import requests
import bs4

# global variables
abs_dir = os.path.dirname(os.path.abspath(__file__)) #<-- absolute path to project directory
# paths to files
path_scrp_dmp = None
path_queries = None
path_log = None
# twitter
q_lines = []
q_length = 0
api = None
# reddit
reddit = None
reddit_subkeys = None


# record certain events in log.txt
def log(s):
    t = strftime("%Y%b%d %H:%M:%S", localtime()) + " " + s

    with open(path_log, 'a') as l:
        l.write(t + "\n")

    # also print truncated log to screen
    p = t[:90] + (t[90:] and '..')
    print(p)

def wait(min, max):
    wt = randint(min, max)
    print("sleeping " + str(wt) + "s...")
    sleep(wt)

def authReddit():
    global reddit
    global reddit_subkeys
    global path_scp_dmp
    global path_queries
    global path_promos
    global path_log

    # get paths to filesk TODO use them for seperate jobs
    #path_scrp_dmp = os.path.join(abs_dir, 'red_scrape_dump.txt')
    #path_queries =  os.path.join(abs_dir, 'red_queries.txt')
    #path_promos =  os.path.join(abs_dir, 'red_promos.txt')
    path_log =  os.path.join(abs_dir, 'red_log.txt')

    print("Authenticating...")

    reddit = praw.Reddit('twotBot')

    log("Authenticated as: " + str(reddit.user.me()));

    # get subreddits, e.g.: androidapps+androiddev+all
    with open('red_subkey_pairs.json') as json_data:
        subkeys_parsed = json.load(json_data)
        reddit_subkeys = subkeys_parsed['sub_key_pairs']

def buildRedDumpLine(submission):
    return (datetime.fromtimestamp(int(submission.created)).strftime("%b%d %H:%M")
            + "SUBM_URL" + str(submission.url)
            + "SUBM_TXT" + submission.selftext.replace("\n", "") + "\n")

def parseRedDumpLine(dl):
    # parse scrape dump file, seperate tweet ids from screen names
    a1 = dl.split('SUBM_URL')
    a2 = a1[1].split('SUBM_TXT')
    # [time, twt_id, scrn_name, twt_txt]
    return [a1[0], a2[0], a2[1]]

def processSubmission(submission):
    # open dump file in read mode
    with open('red_scrape_dump.txt', 'r') as f:
        scrp_lines = f.readlines()

        # if submission already scraped, then return
        if any(str(submission.id) in s for s in scrp_lines):
            return 0

    # otherwise append to red_scrape_dump.txt
    with open('red_scrape_dump.txt', 'a') as f:
        f.write(buildRedDumpLine(submission))
        return 1

def scrapeReddit(scrape_limit, r_new, r_top, r_hot, r_ris):

    def scrape_log(i, k):
        log("Scraped: {total} submissions ({new} new) in {subs}".format(
            total=str(i),
            new=str(k),
            subs=subredstr))

    # search each subreddit combo for new submissions matching its associated keywords
    for subkey in reddit_subkeys:
        i = 0 # total submissions scraped
        k = 0 # new submissions scraped

        subredstr = subkey["subreddits"]
        subreddits = reddit.subreddit(subredstr)

        # search new, hot, or rising categories?
        category = None
        if r_new:
            category = subreddits.new(limit=int(scrape_limit))
            print("Searching new " + str(subreddits))
        elif r_top:
            category = subreddits.top(limit=int(scrape_limit))
            print("Searching top " + str(subreddits))
        elif r_hot:
            category = subreddits.hot(limit=int(scrape_limit))
            print("Searching hot " + str(subreddits))
        elif r_ris:
            category = subreddits.rising(limit=int(scrape_limit))
            print("Searching rising " + str(subreddits))
        else:
            print("Which category would you like to scrape? [-n|-t|-H|-r]")
            sys.exit(1)

        # indefinitely monitor new submissions with: subreddit.stream.submissions()
        for submission in category:
            done = False
            # process any submission with title/text fitting and/or/not keywords
            tit_txt = submission.title.lower() + submission.selftext.lower()

            # must not contain any NOT keywords
            for kw in subkey['keywords_not']:
                if kw in tit_txt:
                    done = True
            if done:
                continue

            # must contain all AND keywords
            for kw in subkey['keywords_and']:
                if not kw in tit_txt:
                    done = True
            if done:
                continue

            # must contain at least one OR keyword
            at_least_one = False
            for kw in subkey['keywords_or']:
                if kw in tit_txt:
                    at_least_one = True
            if not at_least_one:
                continue

            k += processSubmission(submission)
            i += 1
        scrape_log(i, k)

def handleTweepyError(e, scrn_name):
    if "Could not authenticate you" in e.reason:
        log("Authentication failed: check credentials for validity - " + e.reason)
        return 3
    if "Failed to send request" in e.reason:
        log("Failed to SEND request: " + e.reason)
        # wait for 30s before continuing
        wait(30, 30)
        return 0
    if '139' in e.reason:
        log("Skipping: Already favorited/spammed " + scrn_name + " - " + e.reason)
        return 0
    if '136' in e.reason:
        log("Skipping: Blocked from favoriting " + scrn_name + "'s tweets - " + e.reason)
        return 0
    if '144' in e.reason:
        log("Skipping: No status from " + scrn_name + " with that id exists - " + e.reason)
        return 0
    if '226' in e.reason:
        log(e.reason)
        log("Automated activity detected: waiting for next 15m window...")
        return 2
    if '403' in e.reason:
        log("Error querying: please check query for validity, e.g. doesn't exceed max length")
        return 2
    if ('326' in e.reason) or ('261' in e.reason) or ('cannot POST' in e.reason):
        log(e.reason)
        log("Terminal API Error returned: exiting, see log.txt for details.")
        return 3
    if ('89' in e.reason):
        log(e.reason)

# get authentication credentials and tweepy api object
def authTwitter(job_dir):

    global path_scrp_dmp
    global path_queries
    global path_log
    global q_lines
    global q_length
    global api

    # get correct paths to files for current job
    if job_dir:
        cred_path = os.path.join(abs_dir, job_dir + 'credentials.txt')
        path_scrp_dmp = os.path.join(abs_dir, job_dir + 'twit_scrape_dump.txt')
        path_queries = os.path.join(abs_dir, job_dir + 'twit_queries.txt')
        path_log = os.path.join(abs_dir, job_dir + 'log.txt')
    else:
        cred_path = os.path.join(abs_dir, 'credentials.txt')
        path_scrp_dmp = os.path.join(abs_dir, 'twit_scrape_dump.txt')
        path_queries = os.path.join(abs_dir, 'twit_queries.txt')
        path_log = os.path.join(abs_dir, 'log.txt')

    # get authorization credentials from credentials file
    with open(cred_path, 'r') as creds:

        # init empty array to store credentials
        cred_lines = [None] * 6

        # strip end of line characters and any trailing spaces, tabs off credential lines
        cred_lines_raw = creds.readlines()
        for i in range(len(cred_lines_raw)):
            cred_lines[i] = (cred_lines_raw[i].strip())

        print("Authenticating tweepy api...")
        # authenticate and get reference to api
        auth = tweepy.OAuthHandler(cred_lines[0], cred_lines[1])
        auth.set_access_token(cred_lines[2], cred_lines[3])
        api = tweepy.API(auth)

        # ensure authentication was successful
        try:
            log("Authenticated tweepy api as: " + api.me().screen_name)
        except tweepy.TweepError as e:
            handleTweepyError(e, None)
            sys.exit(1)

    # load queries from text file
    with open(path_queries, 'r') as queryFile:
        q_lines = queryFile.readlines()

    # get number of queries
    q_length = sum(1 for _ in q_lines)

def buildDumpLine(tweet):
    return (tweet.created_at.strftime("%b%d %H:%M")
                + "TWT_ID" + str(tweet.id)
                + "SCRN_NAME" + tweet.user.screen_name
                + "TWT_TXT" + tweet.text.replace("\n", "") + "\n")

def parseDumpLine(dl):
    # parse scrape dump file, seperate tweet ids from screen names
    try:
        a1 = dl.split('TWT_ID')
        a2 = a1[1].split('SCRN_NAME')
        a3 = a2[1].split('TWT_TXT')
        # [time, twt_id, scrn_name, twt_txt]
        return [a1[0], a2[0], a3[0], a3[1]]
    except IndexError:
        raise IndexError

def processTweet(tweet, pro, fol, dm):

    scrn_name = tweet.user.screen_name

    # open dump file in read mode
    with open(path_scrp_dmp, 'r') as f:
        scrp_lines = f.readlines()

        # if tweet already scraped, then return
        if any(str(tweet.id) in s for s in scrp_lines):
            return 0

    # otherwise append to twit_scrape_dump.txt
    new_line = buildDumpLine(tweet)
    with open(path_scrp_dmp, 'a') as f:
        f.write(new_line)

    return 1 # return count of new tweets added to twit_scrape_dump.txt


# continuously scrape for tweets matching all queries
def scrapeTwitter(con, eng):

    def report_scrapes(i, k):
            log(("Scraped: {total} tweets ({new} new) found with: {query}\n".format(
            total=str(i),
            new=str(k),
            query=query.replace("\n", ""))))

    print("Scraping...")

    for query in q_lines:
        c = None
        if eng:
            c = tweepy.Cursor(api.search, q=query, lang='en').items()
        else:
            c = tweepy.Cursor(api.search, q=query).items()
        i = 0 # total tweets scraped
        k = 0 # new tweets scraped
        while True:
            try:
                # prompt user to continue scraping after 50 results
                if (not con and i%51 == 50):
                    query_trunc = query[:20] + (query[20:] and '..')
                    keep_going = input("{num} results scraped for {srch}, keep going? (Y/n):".format(num=str(i), srch=query_trunc))
                    if (keep_going != "Y"):
                        raise StopIteration()
                # process next tweet
                k += processTweet(c.next(), pro, fol, dm)
                i += 1
            except tweepy.TweepError as e:
                ret_code = handleTweepyError(e, None)
                if ret_code is 2: # HTTPError returned from query, move onto next query
                    break

                report_scrapes(i, k)
                log("Reached API window limit: taking 15min smoke break..." + e.reason)
                # wait for next request window to continue
                wait(60 * 15, 60 * 15 + 1)
                continue
            except StopIteration:
                report_scrapes(i, k)
                break


# get command line arguments and execute appropriate functions
def main(argv):
    # for logging purposes
    start_time = datetime.now()

    def report_job_status():
        # TODO report
        log("Total run time: " + str(datetime.now() - start_time))

    # catch SIGINTs and KeyboardInterrupts
    def signal_handler(signal, frame):
        log("Current job terminated: received KeyboardInterrupt kill signal.")
        report_job_status()
        sys.exit(0)
    # set SIGNINT listener to catch kill signals
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser(description="Beep, boop.. I'm a social media research bot - Let's get to it!")

    subparsers = parser.add_subparsers(help='platforms', dest='platform')

    # Twitter arguments
    twit_parser = subparsers.add_parser('twitter', help='Twitter: scrape for queries')
    twit_parser.add_argument('-j', '--job', dest='JOB_DIR', help="choose job to run by specifying job's relative directory")

    group_scrape = twit_parser.add_argument_group('query')
    group_scrape.add_argument('-s', '--scrape', action='store_true', dest='t_scr', help='scrape for tweets matching queries in twit_queries.txt')
    group_scrape.add_argument('-c', '--continuous', action='store_true', dest='t_con', help='scape continuously - suppress prompt to continue after 50 results per query')
    group_scrape.add_argument('-e', '--english', action='store_true', dest='t_eng', help='return only tweets written in English')

    # Reddit arguments
    reddit_parser = subparsers.add_parser('reddit', help='Reddit: scrape subreddits')
    reddit_parser.add_argument('-s', '--scrape', dest='N', help='scrape subreddits in subreddits.txt for keywords in red_keywords.txt; N = number of posts to scrape')
    categories = reddit_parser.add_mutually_exclusive_group()
    categories.add_argument('-n', '--new', action='store_true', dest='r_new', help='scrape new posts')
    categories.add_argument('-t', '--top', action='store_true', dest='r_top', help='scrape top posts')
    categories.add_argument('-H', '--hot', action='store_true', dest='r_hot', help='scrape hot posts')
    categories.add_argument('-r', '--rising', action='store_true', dest='r_ris', help='scrape rising posts')

    executed = 0 # catches any command/args that fall through below tree
    args = parser.parse_args()

    # twitter handler
    if args.platform == 'twitter':
        # get authentication credentials and api
        authTwitter(args.JOB_DIR)

        # scrape twitter for all queries
        if args.t_scr:
            scrapeTwitter(args.t_con, args.t_eng)
            executed = 1

        else: # otherwise analyze entries in scrape_dump file
            # get scrape dump lines
            f = open(path_scrp_dmp, "r")
            scrp_lines = f.readlines()
            f.close()


            for i in range(len(scrp_lines)):
                try:
                    pd = parseDumpLine(scrp_lines[i])
                except IndexError:
                    log("Error parsing dump line {ln}: check for validity.".format(ln=str(i + 1)))

                # ignore lines beginning with '-'
                if pd[0][0] == '-':
                    continue

                twt_id = pd[1]
                scrn_name = pd[2]

                # TODO stuff
                
            log("Job completed.")
            report_job_status()

            executed = 1

    # reddit handler
    if args.platform == 'reddit':
        authReddit()

        if args.N:
            scrapeReddit(args.N, args.r_new, args.r_top, args.r_hot, args.r_ris)
            executed = 1

    if not executed:
        log("Unknown Execution Error")
        parser.print_help()
        sys.exit(1)



# so main() isn't executed if file is imported
if __name__ == "__main__":
    # remove first script name argument
    main(sys.argv[1:])

