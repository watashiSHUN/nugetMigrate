import zipfile
import subprocess
#import xmlwitch
import os
import requests
import xml.etree.ElementTree as etree

feedUrl = 'http://www.siteextensions.net/api/v2'
siteExtensionTag = 'siteextension'
nuget = 'nuget.exe'

def editNupkg(listTuples):
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
        for packageId,version in listTuples:
            downloadName = packageId+'.'+version+'.nupkg' # sometimes
            nuspecName = packageId+'.nuspec'
            with zipfile.ZipFile('packages/'+downloadName) as download:
                with zipfile.ZipFile('uploads/'+downloadName,'w') as upload:
                    for zipI in download.infolist(): # zipinfo has compression type
                        if zipI.filename != nuspecName:
                            upload.writestr(zipI,download.read(zipI.filename))#not zipped
                    with download.open(nuspecName) as f:
                        # edit nuspec
                        tree = etree.parse(f)
                        root = tree.getroot()
                        etree.register_namespace('',root.tag[1:root.tag.index('}')])
                        xmlns = {'d':root.tag[1:root.tag.index('}')]}#{http://schemas.microsoft.com/packaging/2010/07/nuspec.xsd}package
                        metaData = root.find('d:metadata',xmlns)
                        siblingTail = metaData[0].tail
                        # insert at position 1
                        # add packageType
                        packageTypes = etree.Element('packageTypes')
                        packageTypes.text = siblingTail+'  '
                        packageType = etree.SubElement(packageTypes,'packageType',attrib={'name':'AzureSiteExtension'})
                        packageType.tail = siblingTail
                        packageTypes.tail = siblingTail
                        metaData.insert(0,packageTypes)
                        tags = metaData.find('d:tags',xmlns)
                        if tags is None: # xml.Element len() shows how many children
                            tags = etree.Element('tags')
                            tags.text = ''
                            tags.tail = siblingTail
                            metaData.insert(0,tags)
                        if not siteExtensionTag in tags.text:
                            #TODO nodediag.nuspec has tag SiteExtension
                            tagsList = tags.text.split()
                            tagsList.append(siteExtensionTag)
                            tags.text = ' '.join(tagsList)

                        upload.writestr(nuspecName,etree.tostring(root))

def downLoadPackages():
    output = subprocess.check_output(['nuget.exe','list','-source',feedUrl],universal_newlines=True) # does not always return the same thing
    listTuples = [lines.split() for lines in output.splitlines()]
    while listTuples[0][1] != '2.2.0':
        # stupid solution
        output = subprocess.check_output(['nuget.exe','list','-source',feedUrl],universal_newlines=True)
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
    return listTuples

def downLoadNuget():
    if not os.path.exists(nuget):
        r = requests.get('https://dist.nuget.org/win-x86-commandline/latest/nuget.exe')
        print('try to download nuget.exe, status code: '+str(r.status_code),flush=True)
        with open(nuget,'wb') as f:
            f.write(r.content)

downLoadNuget()
editNupkg(downLoadPackages())
