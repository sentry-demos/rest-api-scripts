from dotenv import load_dotenv
import os

class FileHandler:

    def migrateFiles(self, platform):
        load_dotenv()
        url = self.constructFilesUrl(platform)
        # DIFFERENT CONDITIONS TO FETCH THE FILES (E.G IF THIS IS A JS PROJECT, THEN WE NEED TO FETCH SOURCEMAPS FROM SPECIFIC RELEASES)

    def constructFilesUrl(self, platform):
        base_url = self.get_on_prem_org_base_url()
        suffix = ""
        if "javascript" in platform:
            suffix = "/files/source-maps/"
        elif "java" in platform:
            suffix = "/files/dsyms/?file_formats=proguard"
        else:
            return suffix
        
        return base_url + "projects/" + os.environ["ON_PREM_ORG_NAME"] + "/" + os.environ["ON_PREM_PROJECT_NAME"] + suffix

    def get_on_prem_org_base_url():
        return os.environ["ON_PREM_URL"]