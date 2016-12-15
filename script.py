import zipfile
import subprocess
#import xmlwitch
import os
import requests
import xml.etree.ElementTree as etree

feedUrl = 'http://www.siteextensions.net/api/v2'
siteExtensionTag = 'siteextension'

def editNupkg(listTuples):
    if not os.path.exists('nuspecs'):
        os.makedirs('nuspecs')
        for packageId,version in listTuples:
            downloadName = packageId+'.'+version+'.nupkg' # sometimes
            print('try to extracts '+downloadName)
            with zipfile.ZipFile('packages/'+downloadName) as zip_ref:
                nuspecName = packageId+'.nuspec'
                print('extracts ' + nuspecName)
                zip_ref.extract(nuspecName,'nuspecs')
    #FIXME do not seperate these steps, pipeline them all together
    for packageId,version in listTuples:
        nuspecName = packageId+'.nuspec'
        relativeFileName = 'nuspecs/'+nuspecName
        with open(relativeFileName,'r+b') as f: #encoding utf-8, not ASCII
            tree = etree.parse(f)
            f.seek(0,0) # reset the file position
            root = tree.getroot()
            etree.register_namespace('',root.tag[1:root.tag.index('}')])
            xmlns = {'d':root.tag[1:root.tag.index('}')]}#{http://schemas.microsoft.com/packaging/2010/07/nuspec.xsd}package
            metaData = root.find('d:metadata',xmlns)
            # add packageType
            packageTypes = etree.SubElement(metaData,'packageTypes')
            packageType = etree.SubElement(packageTypes,'packageType',attrib={'name':'AzureSiteExtension'})
            tags = metaData.find('d:tags',xmlns)
            if tags is None: # xml.Element len() shows how many children
                tags = etree.SubElement(metaData,'tags')
                tags.text = ''
                tags.tail = os.linesep
            if not siteExtensionTag in tags.text:
                tagsList = tags.text.split()
                tagsList.append(siteExtensionTag)
                tags.text = ' '.join(tagsList)
            tree.write(f,xml_declaration=True)

def downLoadPackages():
    output = subprocess.check_output(['nuget.exe','list','-source',feedUrl],universal_newlines=True) # does not always return the same thing
    listTuples = [lines.split() for lines in output.splitlines()]
    if not os.path.exists('packages'):
        os.makedirs('packages')
        for packageId,version in listTuples:
            requestUrl = feedUrl+'/package/'+packageId+'/'+version
            print(requestUrl,flush=True)
            downloadName = packageId+'.'+version+'.nupkg'
            r = requests.get(requestUrl)
            while not r.status_code == requests.codes.ok:
                print('request status code: '+r.status_code + ' retrying...')
                r = requests.get(requestUrl)
            with open('packages/'+downloadName,'wb') as f:
                f.write(r.content)
                #TODO multithreads, while its downloading, edit the file
    return listTuples

editNupkg(downLoadPackages())
