#!/usr/bin/env bash

# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT

plantUmlFilesToGenerate="";
diagramFilesToAddToGitCommit="";
while read -r status plantUmlFile; do

  plantUmlFileWithoutExtension=${plantUmlFile%%.*}

  # clean up image file
  if [[ $status == 'D' ]]; then
    rm "${plantUmlFileWithoutExtension}.png"
  fi


  if [[ $status == 'A' ]] || [[ $status == 'M' ]]; then
    plantUmlFilesToGenerate="${plantUmlFilesToGenerate} ${plantUmlFile}"
    diagramFilesToAddToGitCommit="${diagramFilesToAddToGitCommit} ${plantUmlFileWithoutExtension%%.*}.png"
  fi

done <<< "$(git diff-index --cached HEAD --name-status | grep '\.puml$')"

if [ "${plantUmlFilesToGenerate}" = "" ]
then
  echo No diagrams to render with plantuml
  exit 0
fi

if ! which plantuml 1>& /dev/null
then
  echo "You edited Plantuml diagrams but you don't have plantuml command available. Please install it and try to commit again."
  echo "You can ignore this by adding -n flag to git commit but remember that then you will have outdated diagrams!"
  exit 1
fi

echo "Generating plantuml diagrams for $plantUmlFilesToGenerate"

plantuml "$plantUmlFilesToGenerate"

git add "$diagramFilesToAddToGitCommit"

echo Diagrams are rendered and added to be committed.
