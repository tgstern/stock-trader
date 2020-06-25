# Stock Trading Simulator

Flask application to simulate stock trading portfolio with user accounts.

## Account

Routes to create and login users, saved into SQLite database. Takes form data and saves password hashes
in secure format. There are also options to reset and delete a users account.

## Stocks View

Once logged in, users are directed to homepage showing their portfolio, which is loaded from records in the
SQL database. New users start with $10,000 virtual dollars to begin trading. Users can lookup current values for
each stock by entering the symbol, which are pulled live from IEX API.

## Trade Stocks

Users can buy or sell stocks at the corresponding routes, which save the transaction and price into the database.
Stocks are then added or removed from their portfolio, which updates on the portfolio view page.

> Designed for HarvardX CS50: Introduction to Computer Science
