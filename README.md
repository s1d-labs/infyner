# infyner

Scrape family of s1d labs. It reads public company pages on infyner.com.

- Task `pages`: one queue item holds 50 companies. The task gets `/company/<slug>/<CIN>` for each, stores the page without scripts and styles as `pages/<item>.tar` in the family bucket, and stores the parsed fields as records.
- Fields: current directors with DIN, former name, former-director sentence, size bands, capital, activity, and companies with common directors.
- Only `/company/` pages. The site's robots.txt allows them. No login. No paid tabs (`/ownership/`, `/legal/`, `/documents/`, `/finance/`).
- Slow-down signals (429, 503, many timeouts): the workers wait and the speed goes down. A sustained 403 or challenge page holds the project for a person to decide. Challenge pages are never solved.
- Company lists in `data/` hold CIN and name from the public MCA master.
