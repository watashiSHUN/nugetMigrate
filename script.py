import zipfile
import subprocess
#import xmlwitch
import os
import requests
import xml.etree.ElementTree as etree
import io

feedUrl = 'http://www.siteextensions.net/api/v2'
siteExtensionTag = 'siteextension'
packageTypeName = 'AzureSiteExtension'
nuget = 'nuget.exe'

def printGreen(string,end="",flush=True):
    CSI="\x1B["
    reset=CSI+"m"
    print(CSI+"32m" + string + CSI + "0m", end=end, flush=flush)

def printRed(string,end="",flush=True):
    CSI="\x1B["
    reset=CSI+"m"
    print(CSI+"31m" + string + CSI + "0m", end=end, flush=flush)

def downLoadPackages():
    output = subprocess.check_output(['nuget.exe','list','-source',feedUrl],universal_newlines=True) # does not always return the same thing
    listTuples = [lines.split() for lines in output.splitlines()]
    while listTuples[0][1] != '2.2.0':
        # stupid solution
        output = subprocess.check_output(['nuget.exe','list','-source',feedUrl],universal_newlines=True)
        listTuples = [lines.split() for lines in output.splitlines()]
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
        inMemoryFile = io.BytesIO() # use in memory file object so we can append xml declaration
        for packageId,version in listTuples:
            requestUrl = feedUrl+'/package/'+packageId+'/'+version
            printGreen('download nuget package from: ')
            print(requestUrl,flush=True)
            r = requests.get(requestUrl)
            while not r.status_code == requests.codes.ok:
                printRed('request status code: '+r.status_code + ' retrying...',end=os.linesep)
                r = requests.get(requestUrl)
            # r.content already uses memory
            #maybe multithreading isn't a good idea since memory can explod
            with zipfile.ZipFile(io.BytesIO(r.content)) as download:
                nuspecName = packageId+'.nuspec'
                uploadName = packageId+'.'+version+'.nupkg'
                with zipfile.ZipFile('uploads/'+uploadName,'w') as upload:
                    printGreen('writing to ')
                    print(uploadName,flush=True)
                    for zipI in download.infolist(): # zipinfo has compression type
                        if zipI.filename != nuspecName:
                            upload.writestr(zipI,download.read(zipI.filename))#not zipped
                    with download.open(nuspecName) as f:
                        printGreen('create ')
                        print(nuspecName,flush=True)
                        # edit nuspec
                        tree = etree.parse(f)
                        root = tree.getroot()
                        etree.register_namespace('',root.tag[1:root.tag.index('}')])
                        xmlns = {'d':root.tag[1:root.tag.index('}')]}#{http://schemas.microsoft.com/packaging/2010/07/nuspec.xsd}package
                        metaData = root.find('d:metadata',xmlns)
                        siblingTail = metaData[0].tail
                        # insert at position 0
                        # add packageType
                        packageTypes = etree.Element('packageTypes')
                        packageTypes.text = siblingTail+'  '
                        packageType = etree.SubElement(packageTypes,'packageType',attrib={'name':packageTypeName})
                        packageType.tail = siblingTail
                        packageTypes.tail = siblingTail
                        metaData.insert(0,packageTypes)
                        tags = metaData.find('d:tags',xmlns)
                        if tags is None: # xml.Element len() shows how many children
                            tags = etree.Element('tags')
                            tags.text = ''
                            tags.tail = siblingTail
                            metaData.insert(0,tags)
                        if not siteExtensionTag in tags.text.lower(): # case insensitive
                            #TODO nodediag.nuspec has tag SiteExtension
                            tagsList = tags.text.split()
                            tagsList.append(siteExtensionTag)
                            tags.text = ' '.join(tagsList)
                        inMemoryFile.seek(0,0)#typewriter, set to head before read
                        tree.write(inMemoryFile,xml_declaration=True)
                        inMemoryFile.truncate()#resize inMemoryFile
                        inMemoryFile.seek(0,0)#typewriter, set to head before write
                        upload.writestr(nuspecName,inMemoryFile.read())
        inMemoryFile.close()

def downLoadNuget():
    if not os.path.exists(nuget):
        r = requests.get('https://dist.nuget.org/win-x86-commandline/latest/nuget.exe')
        print('try to download nuget.exe, status code: '+str(r.status_code),flush=True)
        with open(nuget,'wb') as f:
            f.write(r.content)

def publishPackages():
    # need to setapikey beforehand
    for fname in os.listdir('uploads'):
        subprocess.run(['nuget.exe','push','uploads/'+fname,'-source','https://www.myget.org/F/shunsiteextensiontest/api/v2'])
        #nuget push SamplePackage.1.0.0.nupkg <your access token> -Source https://www.myget.org/F/shunsiteextensiontest/api/v2/package

downLoadNuget()
downLoadPackages()
#publishPackages()
