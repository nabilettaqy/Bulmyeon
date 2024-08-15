# bulmyeon (cringe and discontinued)

<p align="center">
  <img src="images/logo.png" />
</p>

Welcome to bulmyeon - A Web App dedicated to voting for the most beautiful girls! This Full Stack development project includes a voting system, leaderboard, and an API for accessing the results and a lot more...

## Bulmyeon

"Bulmyeon" (불면) in Korean literally translates to "insomnia" in English. It is a term used to describe the inability to sleep or a sleep disorder where a person has difficulty falling asleep or staying asleep.

## Features

![Main](images/index.png)

- **Voting System:** Users can vote for the girl they consider the most beautiful.
- **Leaderboard:** Real-time ranking of the most popular girls.
- **Admin Dashboard:** View and manage vote data in a simple and intuitive interface.
- **Moderation:** Delete votes and girls from the database via the Admin Dashboard and Curl (Command-line tool).
- **Mobile-Friendly:** Designed to be accessible on mobile devices.
- **Responsive:** Designed to scale to multiple devices.
- **Latest Votes:** View the latest votes in the main page.
- **API:** Access vote and girls data through an API to integrate results and girls data into other applications.
- **Automated Images Moderation:** NSFW and Hardcore images detection, to have only safe and good content.
- **Submition system:** Users can upload a girl (with images) and have a link to share with other users. 
- **Report system:** Users can report inappropriate content and images.
- **Hardcore images detection:** NSFW and Hardcore images detection, to have only safe and good content.
- **Verified girls:** Girls with a verified badge are the girls that have been verified by the admins/moderators.
- **Ads system:** Ads/supporters system to monetize the project.
- **Girl promotional links:** Girls can share a promotional link (ex: Tikitok, Onlyfans...) to promote their social media accounts. 


## Technologies Used

- **Flask:** Python Web framework for the backend.
- **Python:** Python Programming Language. 
- **HTML, CSS, JavaScript:** Front-end technologies for an interactive user experience.
- **PicoCSS:** Not bloated CSS framework and very lightweight. 
- **SQLite:** Database for storing vote and girls data.
- **Bootstrap:** CSS framework for responsive design (For the Admin page).
- **Curl:** Command-line tool for transferring data (For the API and Moderation Actions like deleting Votes, Girls...).
- **ModerateContent:** API from moderatecontent.com for Moderating Content (Only allow Softcore Images).

## Moderation Actions via Curl

- **Delete a Girl (and everything related to her):** `curl -X DELETE http://localhost:5000/xadmin/purge_girl/girl_name`
- **Delete a Girl (just her query in the database):** `curl -X DELETE http://localhost:5000/xadmin/delete_girl/girl_name`
- **Delete all votes of a Girl (only from VotesLogs):** `curl -X DELETE http://localhost:5000/xadmin/delete_votes/girl_name`
- **Delete a image:** `curl -X DELETE http://localhost:5000/xadmin/delete_image/folder/filename`
- **Purge Unused Images (This will delete all images and folders not present in the database):** `curl -X DELETE http://localhost:5000/xadmin/clean_images`

## Public API

To access vote data via the API, use the following endpoints:

- **GET /api/v1/latestvotes:** Get vote results.
- **GET /api/v1/girl:** Get all girls data.
- **GET /api/v1/girl/<girl_name>:** Get a specific girl data.
- **GET /api/v1/top100:** Get the leaderboard (100 girls).
- **GET /api/v1/latestgirls:** Get latest Added Girls.
- **GET /api/v1/onlyverified:** Get only verified girls.

Note: This is a public API, everyone can access the data.

## Installation

1. Clone the repository: `https://github.com/currentlyonciawatchlist/Bulmyeon.git`
2. `cd bulmyeon`
3. (optional) Create a python virtual environment. 
4. Install dependencies: `pip install -r requirements.txt`
5. Change the settings in the `bulmyeon/app.py` file (ModerateContent API, Secret Keys...).
6. Run the application (in development mode only): `python debug_run.py`

## Deploy

See this [guide](https://dev.to/brandonwallace/deploy-flask-the-easy-way-with-gunicorn-and-nginx-jgc) for deploying the application in a linux server using Nginx and Gunicorn.

Note: The `wsgi.py` file is stored in `/bulmyeon`

## Disclaimer

This project is for educational purposes only. Any actions and or activities related to the material contained within this project is solely your responsibility. I assume no liability and are not responsible for any misuse or damage caused by this program.

## Contact

Created by [Nabil Et-taqy](https://github.com/nabilettaqy) - feel free to contact me!
