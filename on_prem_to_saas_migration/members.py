class Members:

    def populate_members(self, members):
        self.members = members

    def populate_teams(self, teams):
        self.teams = teams

    def getUserID(self, email):
        if email is not None:
            for member in self.members:
                if member["email"] == email:
                    return member["user"]["id"]
        return None

    def getTeamID(self, name):
        if name is not None:
            for team in self.teams:
                if team["slug"].lower() == name.lower() or team["name"].lower() == name.lower():
                    return team["id"]

        return None


    def print(self):
        print(self.members)