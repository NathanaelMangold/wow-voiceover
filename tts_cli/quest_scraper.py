from bs4 import BeautifulSoup
import requests

def get_quest_info(quest_id :int) -> dict:
    # German Constants
    quest_description_german = "Beschreibung"
    quest_complete_description_german = "Vervollständigung"

    # URL
    base_url = "https://www.wowhead.com/wotlk/de/quest="
    #quest_id = 7876
    #quest_id = 160
    #quest_id = 12512
    #quest_id = 7401
    url = base_url + str(quest_id)

    result = requests.get(url)
    website_txt = result.text.replace("<br>", "").replace("</br>", "").replace("<br/>", "").replace("<br />", "")
    doc = BeautifulSoup(website_txt, "html.parser")

    exists = doc.find(class_="database-detail-page-not-found-message")
    if exists != None:
        print("Quest with id " + str(quest_id) + " does not exist")
        return {
            "success" : False
        }


    # Format Special Characters
    format_characters = {
        "<Name>" : "$N",
        "<Klasse>" : "$C",
        "<seinen Kampfgenossen/seine Kampfgenossin>" : "$gbrothers:sisters",
        "<Volk>":"$r",
    }

    # Get Quest Title
    quest_title_class = "heading-size-1"
    title_html = doc.find(class_=quest_title_class)
    quest_title = title_html.contents[0]
    print("Quest Title: " + quest_title)

    # Get Description
    quest_description = ""
    if doc.find(string=quest_complete_description_german):
        description_path_begin = "h2.heading-size-3:nth-of-type(1)"
        description_path_end = "h2.heading-size-3:nth-of-type(2)"

        description_begin_title = doc.select_one(description_path_begin)
        description_end_title = doc.select_one(description_path_end)

        text_elements = []
        current_element = description_begin_title.next_siblings

        for sibling in current_element:
            # Is next Chapter we do not want
            if sibling == description_end_title:
                break

            text = ""
            if isinstance(sibling, str):
                text = sibling.strip()
            else:
                text = sibling.get_text(strip=True)
            
            if text:
                text_elements.append(text)

        quest_description = " ".join(text_elements)
    else:
        description_path_begin = "h2.heading-size-3:nth-of-type(1)"

        description_begin_title = doc.select_one(description_path_begin)

        quest_description = description_begin_title.next_sibling

    print("Quest Description: " + quest_description)

    # Complete Quest Description
    quest_complete_description_class = "lknlksndgg-completion"
    complete_description_html = doc.find(id=quest_complete_description_class)
    quest_complete_description = ""
    if complete_description_html:
        quest_complete_description = complete_description_html.get_text(separator=" ")

    print("Quest Complete Description: " + quest_complete_description)

    return {
        "title" : quest_title,
        "description" : quest_description,
        "complete_description" : quest_complete_description,
        "success" : True
    }

get_quest_info(590)