# Exporting your data

Any workspace member can export a single board as a CSV file from the board menu, using Export > CSV.

Workspace admins can export the whole workspace as JSON from Settings > Data > Export workspace. The export includes boards, cards, comments and member lists. When the export is ready, a download link is emailed to the admin. Export links are valid for 7 days.

For automated or recurring exports, the REST API can read all workspace data. Create a personal access token in Settings > Developer and send it in the Authorization header of each request.

Exports contain only data the person exporting is allowed to see. Deleted boards are not included once the 30 day trash period has passed.
