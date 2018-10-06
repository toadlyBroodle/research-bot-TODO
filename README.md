# social-research-bot
A semi-autonomous bot for researching (scraping, filtering, analyzing) social media sites (reddit, twitter; [TODO: instagram, facebook]) using customizable queries (user, hashtag, and keyword combinations).
Coded in python3 and bash for command-line (CLI).

## features
- Reddit [TODO]
	- scrape subreddit(s) for lists of keywords
		- seperate keyword lists for AND, OR, NOT search operations (red_subkey_pairs.json)
		- search new, hot, or rising categories
	- dump results in local file (red_scrape_dump.txt)

- Twitter [TODO]
	- scrape twitter for list of custom queries
		- scan continuously or in overwatch mode
	- dump results in local file (twit_scrape_dump.txt)
	- research new keywords, hashtags, users by gleening scraped results
	- filter out irrelevant keywords, hashtags, screen names
	- automated scraping, filtering, and analyzing jobs
	- maintain multiple jobs for seperate research projects

## dependencies
- install dependencies you probably don't have already (errors will show up if you're missing any others)
	- install pip3 `sudo apt install python3-pip`
	- install dependencies `pip3 install --user tweepy bs4 praw`

## reddit initial setup
- <a href="https://praw.readthedocs.io/en/v4.0.0/getting_started/configuration/prawini.html">update 'praw.ini'</a> with <a href="https://www.reddit.com/prefs/apps/">your reddit app credentials</a>
	- <a href="http://pythonforengineers.com/build-a-reddit-bot-part-1/">how to register a new reddit app</a>
- replace example promotions (red_promos.txt) with your own
- replace example subreddits and keywords (red_subkey_pairs.json) with your own
	- you'll have to follow the existing json format
	- `keywords_and`: all keywords in this list must be present for positive matching result
	- `keywords_or`: at least one keyword in this list must be present for positive match
	- `keywords_not`: none of these keywords can be present in a positive match
	- any of the three lists may be omitted by leaving it empty - e.g. `"keywords_not": []`

<praw.ini>
```
...

[bot1]
client_id=Y4PJOclpDQy3xZ
client_secret=UkGLTe6oqsMk5nHCJTHLrwgvHpr
password=pni9ubeht4wd50gk
username=fakebot1
user_agent=fakebot 0.1
```

<red_subkey_pairs.json>
```
{"sub_key_pairs": [
{
  "subreddits": "androidapps",
  "keywords_and": ["list", "?"],
  "keywords_or": ["todo", "app", "android"],
  "keywords_not": ["playlist", "listen"]
}
]}
```

## reddit usage
[TODO]

## twitter initial setup
- create new directory to store new job data
- create new 'credentials.txt' file in job directory to store your twitter app's credentials
	- <a href="https://www.digitalocean.com/community/tutorials/how-to-create-a-twitterbot-with-python-3-and-the-tweepy-library">a good guide for how to get twitter credentials</a>

<credentials.txt>
```
your_consumer_key
your_consumer_secret
your_access_token
your_access_token_secret
your_twitter_username
your_twitter_password
```

- create new 'twit_queries.txt' in job directory to store your job's queries to scrape twitter for
	- individual queries on seperate lines
	- <a href="https://dev.twitter.com/rest/public/search">guide to constructing twitter queries</a>
- create new 'twit_scrape_dump.txt' file to store your job's returned scrape results

## twitter usage
[TODO]

## twitter example workflows
1) continuous mode
	- `-cspf` scrape and promote to all tweets matching queries
2) overwatch mode
	- `-s` scrape first
	- manually edit twit_scrape_dump.txt
		- add '-' to beginning of line to ignore
		- leave line unaltered to promote to
	- `-pf` then promote to remaining tweets in twit_scrape_dump.txt
3) gleen common keywords, hashtags, screen names from scrape dumps
	- `bash gleen_keywords_from_twit_scrape.bash`
		- input file: twit_scrape_dump.txt
		- output file: gleened_keywords.txt
            - results ordered by most occurrences first
4) filter out keywords/hashtags from scrape dump
    - manually edit gleened_keywords.txt by removing all relevent results
    - `filter_out_strings_from_twit_scrape.bash`
        - keywords input file: gleened_keywords.txt		
        - input file: twit_scrape_dump.txt
		- output file: twit_scrp_dmp_filtd.txt
5) automatic scrape, filter, analyze
	- `auto_research.bash`
		- automatically scrape twitter for queries, filter out irrelevant results, and analyze relevant results
7) specify job
    - `-j bitcoin/` specify which job directory to execute

## notes
If you don't want to maintain individual jobs in separate directories, you may create single credentials, queries, promos, and scrape dump files in main working directory.

Future updates will include modules for researching instagram and facebook, giant-flying-spaghetti-monster willing.
