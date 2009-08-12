# -*- coding: utf-8 -*-

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import email
import smtplib
import string
import time
import MySQLdb
import feedparser

import config

if __name__ == "__main__":
    sendEmail = False
    lastupdate = time.localtime(0)
    timefile = open("lastupdate", "r+")
    
    try:
        lastupdate = time.strptime(timefile.readline())
    except ValueError:
        pass
    
    paragraphRE = re.compile(r"<p.*>.*</p>")
    
    conn = MySQLdb.connect (host = config.dbHost,
                            user = config.dbUser,
                            passwd = config.dbPassword,
                            db = config.dbDatabase)
    cursor = conn.cursor ()

    msg = email.Message.Message()
    
    msg['From'] = config.feederEmail
    msg['To'] = string.join(config.admins, ", ")
    msg['Subject'] = "New feeds awaiting for Approval"
    msg['Content-type'] = "multipart/mixed"
    
    for feedurl in config.subscribedFeeds:
        feedInfo = feedparser.parse(feedurl)
        
        for entry in feedInfo.entries:
            if entry.updated_parsed < lastupdate:
                continue
            
            sendEmail = True
            thissummary = ""
            payload = "<h2>" + entry.title + "</h2>"
            payload += "<h3>" + entry.author + "</h3>"
            payload += "<a href=\"" + entry.link + "\">" + entry.link + "</a><br>"
          
            if entry.has_key('summary'):
                thissummary = entry.summary
                payload += entry.summary
            else:
                paragraphs = paragraphRE.findall(entry.content[0].value)
                if (not paragraphs):
                    thissummary = entry.content[0].value 
                    payload += entry.content[0].value
                else:
                    thissummary = paragraphs[0]
                    payload += paragraphs[0] 
                
            m = email.Message.Message()
            m.add_header("Content-type", "text/html")
            m.set_payload(payload.encode("utf-8"), "utf-8")
            msg.attach(m)

            insertquery = """
INSERT INTO %(tablename)s (%(tablename)s.title, %(tablename)s.alias, %(tablename)s.introtext, %(tablename)s.fulltext,
                         %(tablename)s.state, %(tablename)s.sectionid, %(tablename)s.catid,
                         %(tablename)s.created, %(tablename)s.created_by, %(tablename)s.modified, %(tablename)s.modified_by, %(tablename)s.checked_out, %(tablename)s.checked_out_time, %(tablename)s.publish_up,
                         %(tablename)s.images, %(tablename)s.urls, %(tablename)s.attribs, %(tablename)s.metakey, %(tablename)s.metadesc, %(tablename)s.metadata)
VALUES ('%(title)s', '%(alias)s', '%(intro)s', '%(full)s',
        0, %(newsId)d, %(planetId)d,
        NOW(), %(planetUser)d, NOW(), %(planetUser)d, %(planetUser)d, NOW(), NOW(),
        '', '', '%(attribs)s', '', '', '')
"""%{'tablename':config.dbContentTable,
     'title':string.replace(entry.title, "'","\'"),
     'alias':string.replace(string.replace(string.lower(entry.title), " ", "-"), "'", "\'"),
     'intro':string.replace(thissummary, "'", "\'"),
     'full':string.replace(entry.content[0].value, "'", "\'"),
     'newsId':config.planetSectionId,
     'planetId':config.planetCategoryId,
     'planetUser':config.planetUserId,
     'attribs':"""
show_title=
link_titles=
show_intro=
show_section=
link_section=
show_category=
link_category=
show_vote=
show_author=0
show_create_date=
show_modify_date=
show_pdf_icon=
show_print_icon=
show_email_icon=
language=
keyref=
readmore=
"""}
            cursor.execute(insertquery)

    if sendEmail:           
        server = smtplib.SMTP(config.smtpServer)
        server.sendmail(config.feederEmail, string.join(config.admins, ", "), msg.as_string())
        server.quit()
    
    timefile.write(time.ctime(time.mktime(time.localtime())))
    
    
    