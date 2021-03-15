"""
Savings (with) Ai Viewing Reddit
Developed by Ian Reichard
github.com/ireichard
"""

import os
import sys
import math
import pandas as pd  # Data science and AI library
import pygame  # Great library for a simple gui application
import pygame_gui
import praw  # Reddit scraping library. Some setup to use this is required such as a reddit API key, refer to praw documentation for details.
from praw.util.token_manager import FileTokenManager
import pyperclip  # Allows python to copy stuff to clipboard

# Weights used to determine how good a product is for recommendation.
savr_score_comment_weight = 1.1
savr_score_upvote_weight = 1.4

num_posts = 50
target_reddit_str = 'buildapcsales'

# Some terms like 'm.2 ssd' and 'sata ssd' are separated, but are both ssds. This consolidates both of these terms into 1 term.
formatted_strings = ['ssd']

# Define common terms used to describe certain parts. Helps avoid issues with parts not being labelled correctly on reddit and leading to it not being parsed.
# Index 0 of these sublists is what the program will change the other terms to. Ex. 'processor' is index 1, will be changed to index 0 or 'cpu'.
redefined_terms = [['cpu', 'processor'],
                   ['motherboard', 'mobo'],
                   ['ram', 'memory'],
                   ['gpu', 'graphics', 'graphics card', 'video card', 'geforce', 'radeon'],
                   ['aio', 'radiator'],
                   ['fans', 'fan'],
                   ['other', 'meta']]  # Some terms aren't for specific parts, called 'meta' or 'other'. These are the identifying keywords for these parts

# Terms to actually search for
items = ['aio', 'cpu', 'motherboard', 'ram']


# noinspection PyGlobalUndefined
def gui():
    """
    Builds GUI for application.
    """
    pygame.init()
    pygame.display.set_caption('SAVR: Savings (with) Ai Viewing Reddit')
    window_surface = pygame.display.set_mode((1200, 800))
    background = pygame.Surface((1200, 800))
    background.fill(pygame.Color('#212121'))
    pygame.display.set_icon(pygame.image.load('icon.png'))
    manager = pygame_gui.UIManager((1200, 800))

    # First start with number of reddit posts to reference.
    post_str = 'Total Posts to Query:'
    queries = [5, 10, 20, 40, 80, 200]
    queries_start = 230
    queries_size = 40
    # pygame_gui.elements.UI
    # pygame.Rect is left top width height in that order
    pygame_gui.elements.UILabel(relative_rect=pygame.Rect((40, 10), (180, 30)), text=post_str, manager=manager)
    selection_button = []
    for i in range(len(queries)):
        selection_button.append(pygame_gui.elements.UIButton(relative_rect=pygame.Rect((queries_start, 10), (queries_size, 30)), text=str(queries[i]), manager=manager))
        queries_start += queries_size + 10
    global num_posts_selected
    num_posts_selected = 0
    query_selected_ui = pygame_gui.elements.UILabel(relative_rect=pygame.Rect((590, 10), (120, 30)), text='Selected: ' + str(num_posts_selected), manager=manager)

    # Types of computer parts comes next.
    parts = ['CPU', 'AIO', 'Motherboard', 'RAM', 'GPU', 'SSD', 'HDD', 'Case', 'Fans', 'Monitor', 'Keyboard', 'Mouse']
    parts_start = 230
    parts_size = 100
    pygame_gui.elements.UILabel(relative_rect=pygame.Rect((40, 60), (180, 30)), text='Select hardware:', manager=manager)
    parts_selection = []
    for i in range(8):
        parts_selection.append(pygame_gui.elements.UIButton(relative_rect=pygame.Rect((parts_start, 60), (parts_size, 30)), text=str(parts[i]), manager=manager))
        parts_start += parts_size + 10
    parts_start = 230
    for i in range(len(parts)):
        if i > 7:
            parts_selection.append(pygame_gui.elements.UIButton(relative_rect=pygame.Rect((parts_start, 110), (parts_size, 30)), text=str(parts[i]), manager=manager))
            parts_start += parts_size + 10
    parts_selected_ui = pygame_gui.elements.UILabel(relative_rect=pygame.Rect((40, 160), (1100, 30)), text='Selected: ', manager=manager)
    parts_selected = []

    # Go Button for search.
    go_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((40, 210), (180, 30)), text='GO!', manager=manager)

    # Finally, placeholders for reddit links with strings.
    global reddit_info
    reddit_info = pd.DataFrame()
    y_start_reddit_ui_elements = 260
    reddit_ui_elements = [['SAVR Score', 'Part', 'Price', 'Reddit Link', 'Store Link']]
    reddit_ui_sizes = [150, 300, 400, 100, 100]
    reddit_ui_size_current = 40
    reddit_ui_header = []
    for i in range(len(reddit_ui_sizes)):  # Display titles from reddit_ui_elements
        reddit_ui_header.append(pygame_gui.elements.UILabel(relative_rect=pygame.Rect((reddit_ui_size_current, y_start_reddit_ui_elements), (reddit_ui_sizes[i], 30)), text=reddit_ui_elements[0][i], manager=manager))
        reddit_ui_size_current += 10 + reddit_ui_sizes[i]
    reddit_ui_size_current = 40
    reddit_ui = []
    for i in range(10):  # Fills in filler text
        reddit_ui_elements.append(['[None]', '[None]', '[None]', '[None]', '[None]'])
    y_start_reddit_ui_elements = 310
    for i in range(10):  # Display top 10 results in buttons
        ui_add = []
        for j in range(3):
            ui_add.append(pygame_gui.elements.UIButton(relative_rect=pygame.Rect((reddit_ui_size_current, y_start_reddit_ui_elements), (reddit_ui_sizes[j], 30)), text=reddit_ui_elements[i+1][j], manager=manager))
            reddit_ui_size_current += 10 + reddit_ui_sizes[j]
        for j in range(2):
            ui_add.append(pygame_gui.elements.UIButton(relative_rect=pygame.Rect((reddit_ui_size_current, y_start_reddit_ui_elements), (reddit_ui_sizes[j+3], 30)), text=reddit_ui_elements[i + 1][j+3], manager=manager))
            reddit_ui_size_current += 10 + reddit_ui_sizes[j+3]
        reddit_ui.append(ui_add)
        reddit_ui_size_current = 40
        y_start_reddit_ui_elements += 30

    clk = pygame.time.Clock()
    running = True

    def show_image(f, x, y):
        """Cleans up some code by placing here."""
        window_surface.blit(f, (x, y))

    reddit = False
    reddit_done = False
    while running:
        if reddit:
            reddit_info = get_reddit_data(target_items=parts_selected, total_threads=num_posts_selected).copy(deep=False)
            # print(reddit_info)
            indexes = reddit_info.index.values.tolist()
            # print(indexes)
            order = ['scores', 'part_type', 'prices', 'post_url', 'url']
            for i in range(reddit_info.shape[0]):
                if i < 10:
                    for j in range(len(reddit_ui[i])):
                        reddit_ui[i][j].set_text(str(reddit_info.at[indexes[i], order[j]]))
            reddit = False
            reddit_done = True
        time_delta = clk.tick(60)/1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:  # iterate through elements to find exact button pushed
                    for i in range(len(selection_button)):
                        if event.ui_element == selection_button[i]:
                            query_selected_ui.set_text('Selected: ' + str(queries[i]))
                            num_posts_selected = queries[i]
                    for i in range(len(parts_selection)):
                        if event.ui_element == parts_selection[i]:
                            parts_selected.append(parts_selection[i].text.lower())
                            parts_selected_ui.set_text(parts_selected_ui.text + parts_selection[i].text + ' ')
                    if event.ui_element == go_button:
                        if len(parts_selected) > 0 and num_posts_selected > 0:
                            reddit = True
                    if reddit_done:
                        for i in range(len(reddit_ui)):
                            for j in range(len(reddit_ui[i])):
                                if event.ui_element == reddit_ui[i][j]:
                                    pyperclip.copy(reddit_ui[i][j].text)

            manager.process_events(event)
        manager.update(time_delta)

        show_image(background, 0, 0)

        manager.draw_ui(window_surface)
        pygame.display.update()


def get_reddit_data(target_items, total_threads):
    """
    Returns data from subreddit.
    """
    if not os.path.exists('refresh_token.txt'):
        f = open('refresh_token.txt', 'x')
        f.close()
        print('Please fill in required information in \'refresh_token.txt\'')
        sys.exit()
    if not os.path.exists('bot.txt'):
        f2 = open('bot.txt', 'x')
        f2.close()
        print('Please fill in required information in \'bot.txt\'')
        sys.exit()

    # Authenticate to Reddit
    refresh_token_manager = FileTokenManager('refresh_token.txt')  # Refer to praw documentation for obtaining a refresh token from reddit here: https://praw.readthedocs.io/en/latest/getting_started/authentication.html
    reddit = praw.Reddit(token_manager=refresh_token_manager, user_agent=open('bot.txt', 'r').read())  # Get bot token

    # Scrape Reddit data
    posts = []
    target_reddit = reddit.subreddit(target_reddit_str)
    for post in target_reddit.hot(limit=total_threads):  # Search from top posts in 'hot' category in specified subreddit, limit based on user specification.
        posts.append(
            [post.title,
             post.score,
             post.num_comments,
             post.url,
             post.id,
             post.created])
    posts = pd.DataFrame(posts, columns=['title', 'score', 'num_comments', 'url', 'id', 'created'])  # Build a pandas dataframe
    # Parse useful stuff in the dataframe

    # Type of product
    titles = []
    for i in range(posts.shape[0]):  # df.shape[0] = number of rows
        titles.append(posts.at[i, 'title'])
    part_type = []
    for i in range(len(titles)):  # Get only the part types from title of post
        name = titles[i]
        index = -1
        for j in range(len(name)):
            if name[j] == '[' and index > -2:
                index = j+1
            elif name[j] == ']' and index > -1:
                part_type.append(name[index:j].lower())
                index = -2  # Prevents string from getting screwed up while parsing extra ]
        if index == -1:
            part_type.append('')
    # Certain part types require additional parsing for formatting. Ex. 'm.2 ssd' can be parsed to just 'ssd'.
    for i in range(len(part_type)):
        for j in range(len(formatted_strings)):
            if formatted_strings[j] in part_type[i]:
                part_type[i] = formatted_strings[j]

    # Certain part types aren't always labelled correctly. Go through terms and set them to term[0] (see redefined_terms definition for more info)
    for i in range(len(part_type)):
        for j in range(len(redefined_terms)):
            for k in range(len(redefined_terms[j])):
                if redefined_terms[j][k] in part_type[i]:
                    part_type[i] = redefined_terms[j][0]

    posts['part_type'] = part_type  # add part types to dataframe

    # Price range
    prices = []
    found = False
    for i in range(len(titles)):
        skip_rest = False
        for j in range(len(titles[i])):
            if titles[i][j] == '$' and not skip_rest:
                found = True
                skip_rest = True
                prices.append(titles[i][j:])
        if not found:
            prices.append('')

    posts['prices'] = prices  # add prices to dataframe
    # posts = posts[2:]  # remove the top posts on the subreddit pinned by moderators
    # posts.to_csv('posts.csv')

    # Get target products
    target_nums = []
    for i in range(len(part_type)):
        for j in range(len(target_items)):
            if part_type[i] == target_items[j]:
                target_nums.append(i)
    # print(target_nums)
    # Make a new dataframe with just target products
    targets = pd.DataFrame(columns=['title', 'score', 'num_comments', 'url', 'id', 'part_type', 'prices'])
    if len(target_nums) > 0:
        for i in range(len(target_nums)):
            targets.loc[posts.index[target_nums[i]]] = posts.iloc[target_nums[i]]  # Copy everything with target numbers over to new dataframe
        # Change indexing of new dataframe to be 0-n
        size = targets.shape[0]
        indicies = [i for i in range(size)]
        targets['index'] = indicies
        targets.set_index('index', inplace=True)
        posts = posts[2:]  # remove the top posts on the subreddit pinned by moderators
    else:
        sys.exit()  # No products to show

    # Get urls to original posts

    post_urls = []
    # print(targets.shape[0])
    # print(targets)
    for i in range(targets.shape[0]):
        # post_urls.append(targets.at[i, 'id'])
        post_urls.append('https://www.reddit.com/r/' + target_reddit_str + '/comments/' + targets.at[i, 'id'] + '/')
    targets['post_url'] = post_urls  # add post urls to dataframe

    # Calculate the SAVR score. Function of 1000 + comment_weight * comments + upvote_weight * upvotes
    scores = []
    for i in range(targets.shape[0]):
        scores.append(math.floor(1000 + targets.at[i, 'score'] * savr_score_upvote_weight + targets.at[i, 'num_comments'] * savr_score_comment_weight))
    targets['scores'] = scores
    targets = targets.sort_values(by=['scores'], ascending=False)  # Sort the dataframe by scores determined by the program.
    # targets.to_csv('targets.csv')
    return targets


def reddit_csv():
    # Authenticate to Reddit
    refresh_token_manager = FileTokenManager('refresh_token.txt')
    reddit = praw.Reddit(token_manager=refresh_token_manager,
                         user_agent=open('bot.txt', 'r').read())

    # Scrape Reddit data
    posts = []
    target_reddit = reddit.subreddit('buildapcsales')
    for post in target_reddit.hot(limit=20):
        posts.append(
            [post.title,
             post.score,
             post.id,
             post.subreddit,
             post.url,
             post.num_comments,
             post.selftext,
             post.created])
    posts = pd.DataFrame(posts, columns=['title', 'score', 'id', 'subreddit', 'url', 'num_comments', 'body', 'created'])
    posts.to_csv('old_posts.csv')


if __name__ == "__main__":
    gui()
    # get_reddit_data(items)
    # reddit_csv()
else:
    print('Run me as the main program!')
