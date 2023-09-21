CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    username TEXT NOT NULL,
    hash TEXT NOT NULL,
    cash NUMERIC NOT NULL DEFAULT 10000.00
);


CREATE TABLE purchase (
    users_id INTEGER NOT NULL,
    stock TEXT NOT NULL,
    shares INTEGER NOT NULL,
    price REAL NOT NULL,
    total_purchase REAL NOT NULL,
    date DATE NOT NULL,
    FOREIGN KEY(users_id) REFERENCES users(id)
);


CREATE TABLE sell (
    users_id INTEGER NOT NULL,
    stock TEXT NOT NULL,
    shares INTEGER NOT NULL,
    price REAL NOT NULL,
    total_sell REAL NOT NULL,
    date DATE NOT NULL,
    FOREIGN KEY(users_id) REFERENCES users(id)
);

CREATE TABLE consolidated (
    users_id INTEGET NOT NULL,
    stock TEXT NOT NULL,
    shares INTEGER NOT NULL,
    FOREIGN KEY(users_id) REFERENCES users(id)
);

which stocks the user owns, the numbers of shares owned,
the current price of each stock, and the total value of each holding(i.e., shares times price).
Also display the user’s current cash balance along with a grand total (i.e., stocks’ total value plus cash).