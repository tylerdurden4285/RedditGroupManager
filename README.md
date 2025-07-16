# Reddit Group Manager
A self hostable docker application that lets you make custom group lists of subreddits and post to them in bulk. It has a Rest API and scheduling feature also. Built in collaboration with Ai (yes I know boo right) but I've found it incredibly useful and want to share it here for public use. 

TLDR (Aka: Get to the point, how do I install it?)
1. copy the .env.example to .env and edit your values accordingly
2. docker compose up --build -d
3. Go to the ports you selected (default is 5015 for frontend and 8015 for backend API)

ENJOY!

## What can you do with it? 
You can:
* Create 'groups' of subreddits around niches/topics
* Preselect your preferred subreddit flairs in groups.
* Post in bulk to those groups all at once. 
* Setup a scheduled post to your chosen subreddit group.
* use the API along with other tools like N8N, Zapier, Curl, python etc for your own integration.

## Who's it suitable for?
People that often post content to multiple groups around specific subjects, topics or niches. This app will allow you to group your posts into different custom categories of topic so you can easily reference and post to them in bulk later. 

For example if you often posted healthy cooking recipes and photos to 12 different subreddit groups you could simply create a group one time called "healthy recipes" and preselect your chosen subreddit flairs, then when you want to post to them all at once you can just create the post one time and bulk post to them all either live or at a future date. 

## What types of posts can I do? 
Currently you can do: 
* Image posts (also gifs)
* Link posts (Follows reddits special media view style for common media link types - like giphy, redgifs, imgur)
* Text posts

## Can I add comments too?
Yes, all post types have the option to add a comment to your post. It's up to you. 

## Raw text only or is it styled? 
Posts and comments use the quill text editor. So you can do things like: 
* Add links
* italics
* headers
* Underline
* hyperlink

## What if I make a mistake
You can undo posts in bulk by selecting them and clicking "undo". You can also repost in the future if you want. Any future scheduled posts can be edited also to a different time or day if needed. 

As you can imagine this is a powerful tool if used correctly. I am just a solo guy doing this as a hobby so if you want to get involved, have any recommendations or request then please do let me know. I have a few things I hope to add when I get time but I welcome additional help if you want to do it yourself then thank you in advance. This has potential to be something really cool. I just did what I can to get it started. 

### FUTURE IDEAS:
1. Analytics and metrics tracking.
2. Respond to other peoples comments in a per post feed.
3. Multiple user switching.
4. Authentik or Google auth login.
5. Text body for images (which seems to be allowed now in reddit).
6. Bulk edit posts. like updating all selected comments or posts to something else (unsure if possible)

RGM has a subreddit here: https://www.reddit.com/r/RedditGroupManager for discussion but if you have any issues please submit them here to ensure they are correctly addressed. 



