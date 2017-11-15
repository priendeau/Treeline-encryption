#!/bin/bash 


unset UpdateTreelineRepository ; 

function UpdateTreelineRepository()
{
	function Verbosis()
	{
		local -a ArrayArg=( $* ) ;
		local -a __call_locality=( Verb Verbosis ) ; 
		local Arg0=${ArrayArg[0]} ; 
		local StrMsg=${VerbMsg:=__TEXT__} ; 
		local StrDevOut=${VerbDev:=/dev/stderr} ; 
		local IsVerboseState=${VerbState:=False} ;
		local StrVerboseHeader=${VerbHeader:=VERBOSE} ;
		local IsEvalRequiredForm=${VerbEvalForm:=False} ; 
		local IsDisplayFormatted=${VerbFormated:=True} ;
		local IsAppendMode=${VerbAppendDev:=False} ; 
		local IsExtendedOutput=${VerbExtendedOut:=False} ; 
		local ArrayArg=( $* ) ; 
		if [ "${IsVerboseState:=False}" == "True" ] ; then 
			if [ "${IsDisplayFormatted:=True}" == "True" ] ; then 
				if [ "${IsAppendMode:=False}" == "True" ] ; then 
						echo -ne "${StrVerboseHeader}:[ ${StrMsg} ]\n" >> ${StrDevOut} ;
				else  
						echo -ne "${StrVerboseHeader}:[ ${StrMsg} ]\n" > ${StrDevOut} ;
				fi
			else
				if [ "${IsEvalRequiredForm:=False}" == "True" ] ; then 
					if [ "${IsExtendedOutput:=False}" == "True" ] ; then 
							echo -ne "${StrMsg}" ;  
					else
							echo "${StrMsg}" ;  
					fi
				else
					if [ "${IsAppendMode:=False}" == "True" ] ; then 
						if [ "${IsExtendedOutput:=False}" == "True" ] ; then 
								echo -ne "${StrMsg}" >> ${StrDevOut} ;
						else
								echo "${StrMsg}" >> ${StrDevOut} ;
						fi
					else
						if [ "${IsExtendedOutput:=False}" == "True" ] ; then 
							echo -ne "${StrMsg}" > ${StrDevOut} ;
						else
							echo "${StrMsg}" > ${StrDevOut} ;
						fi 
					fi
				fi 
			fi 
		fi
	} 
	### Model :VerbMsg=MSG VerbHeader=DEBUG VerbEvalForm=False VerbFormated=True VerbState=True VerbDev=/dev/stderr  Verbosis

 if [ ${versionCA:=0.0.0} == "0.0.0" ] ; then 
  local -a ArrayArg=( $* ) ;
  local -a __call_locality=( UTR UpdateTreelineRepository ) ;
  local Arg0="${ArrayArg[0]}" ; 
  local StrParentApps=${__call_locality[1]} ;
  local StrStartMain=${UTRFuncStart:=__main_StartServices} ; 
 elif [ ${versionCA:=0.0.0} == "0.0.1" ] ; then 
  eval $( eval CAFunctName=UpdateTreelineRepository CAIsAddParent=False __Call_Argument ) ; 
 elif [ ${versionCA:=0.0.0} == "0.0.2" ] ; then 
  eval $( eval CAFunctName=UpdateTreelineRepository UUID=${CAUUID:=None} CAIsAddDebug=True CAProvideDebug=DisplayDebug,DisplayEntry,DisplayCmd CAIsAddParent=False CallArgument ) ;
 fi  
	
	local StrDestinationPath=${UTRDestination:=None} ;
	local StrSourcePath=${UTRSource:=None} ; 
 local StrCSVBloc=${UTRCsvLine:=':'};
 local StrCSVLine=${UTRCsvBloc:=';'}


 function FindTreeLine()
 {
  find ${FTLSourcePath} -type f -iname "*.py" -printf "%f${FTLCsvBloc}%p${FTLCsvLine}" ; 
 }

 local -a ArrayUpdateItem=(  ) ; 
 StrReference=$( FTLCsvBloc="${StrCSVBloc}" FTLCsvLine="${StrCSVLine}" FTLSourcePath="${StrSourcePath}" FindTreeLine ) ;
 local StrASeg ;
 local StrBSeg ;
 local StrCSeg ;
 local StrDSeg ; 
 
 local ArrayMsg=() ;
 ArrayMsg[0]="Destination path:${StrDestinationPath}\nDevelpt Path:${StrSourcePath}" ; 
 ArrayMsg[1]="Initial StrASeg:__SEG__" ; 
 ArrayMsg[2]="BoolDisplayDebug: __DISPLAYDEBUG__\nBoolDisplayCmd: __DISPLAYCMD__" ; 
 ArrayMsg[3]="FindTreeLine Broken down" ; 
 ArrayMsg[4]="File: __FILE__\n\tSHA1SUM-Source:__SRC__\n\tSHA1SUM-Destination:__DEST__" ; 
 ArrayMsg[5]="SHA1SUM Differ from file __FILE__\n\trequire updating destination to reflect changes. " ; 
 ArrayMsg[6]="All File :( __FILE__ ), require to be updated to reflect repository/destination being updated."
 
 StrMsg=${ArrayMsg[0]} ;
 StrMsg=${StrMsg//__DESTPATH__/${StrDestinationPath}} ; 
 StrMsg=${StrMsg//__SRCPATH__/${StrSourcePath}} ; 
	VerbMsg="${StrMsg}" VerbHeader="${__call_locality[1]}-DEBUG" VerbState=${BoolDisplayDebug} VerbEvalForm=False VerbFormated=True VerbDev=/dev/stderr  Verbosis ;

 StrASeg="${StrReference}" ; 
 StrMsg=${ArrayMsg[1]} ;
 StrMsg=${StrMsg//__SEG__/${StrASeg}} ; 
	VerbMsg="${StrMsg}" VerbHeader="${__call_locality[1]}-DEBUG" VerbState=${BoolDisplayDebug} VerbEvalForm=False VerbFormated=True VerbDev=/dev/stderr  Verbosis ;

 
 StrMsg=${ArrayMsg[2]} ;
 StrMsg=${StrMsg//__DISPLAYDEBUG__/${BoolDisplayDebug}} ; 
 StrMsg=${StrMsg//__DISPLAYCMD__/${BoolDisplayCmd}} ; 
	VerbMsg="${StrMsg}" VerbHeader="${__call_locality[1]}-DEBUG" VerbState=${BoolDisplayDebug} VerbEvalForm=False VerbFormated=True VerbDev=/dev/stderr  Verbosis ;

 StrMsg=${ArrayMsg[3]} ;
	VerbMsg="${StrMsg}" VerbHeader="${__call_locality[1]}-DEBUG" VerbState=${BoolDisplayDebug} VerbEvalForm=False VerbFormated=True VerbDev=/dev/stderr  Verbosis ;
 

 local -a ArraySha=( ) ;
 local -a ArrayFileRequireUpdate=( ) ;
 while [ ${StrASeg:="None"} != "None" ] ; do  
  StrBSeg=${StrASeg/%${StrCSVLine}[^${StrCSVLine}]*}
  StrASeg=${StrASeg/#${StrBSeg}${StrCSVLine}} ; 
		#echo -ne "StrASeg: ${StrASeg}\n" ; 
		
		StrMsg="StrBSeg: ${StrBSeg}" ; 
		VerbMsg="${StrMsg}" VerbHeader="${__call_locality[1]}-CMD-DEBUG" VerbState=${BoolDisplayCmd} VerbEvalForm=False VerbFormated=True VerbDev=/dev/stderr  Verbosis ;
		StrCSeg=${StrBSeg} ; 
		ArraySha=( ) ; 
		intCount=0 ; 
		while [ ${StrCSeg:="None"} != "None" ] ; do 
			StrDSeg=${StrCSeg/%${StrCSVBloc}[^${StrCSVBloc}]*}
			if [ ${intCount:=0} -eq 0 ] ; then 
			 ### At loop0, it should:
			 ### feed ArraySha[0] to provide 
			 ### the name for checksuming . 
			 ### Do the checksum for the Source.
			 ArraySha[${#ArraySha[@]}]="${StrDSeg}"
			 ArraySha[${#ArraySha[@]}]=$( sha1sum ${StrSourcePath}/${ArraySha[0]} | cut -d ' ' -f 1 ) ; 
			fi 
			if [ ${intCount:=0} -eq 1 ] ; then 
			 ### At loop1, it should:
			 ### Do the checksum for the Destination.
			 ArraySha[${#ArraySha[@]}]=$( sha1sum ${StrDestinationPath}/${ArraySha[0]} | cut -d ' ' -f 1 ) ; 
		 fi 
		 StrCSeg=${StrCSeg/#${StrDSeg}${StrCSVBloc}} ; 
		 StrMsg="\tStrCSeg: ${StrCSeg}\n\tStrDSeg: ${StrDSeg}"
		 VerbMsg="${StrMsg}" VerbState=${BoolDisplayDebug} VerbHeader="${__call_locality[1]}-CMD-DEBUG"  VerbEvalForm=False VerbFormated=True VerbDev=/dev/stderr  Verbosis ;
		 StrCSeg=${StrCSeg/#${StrDSeg}} ; 
		 intCount=$(( ${intCount} + 1 )) ; 
		done 
		#echo -ne "File: ${ArraySha[0]}\n\tSHA1SUM-Source:${ArraySha[1]}\n\tSHA1SUM-Destination:${ArraySha[2]}\n"
		StrMsg=${ArrayMsg[4]} ;
		StrMsg=${StrMsg//__FILE__/${ArraySha[0]}} ; 
		StrMsg=${StrMsg//__SRC__/${ArraySha[1]}} ; 
		StrMsg=${StrMsg//__DEST__/${ArraySha[2]}} ; 
		VerbMsg="${StrMsg}" VerbHeader="${__call_locality[1]}-DEBUG" VerbState=True VerbEvalForm=False VerbFormated=True VerbDev=/dev/stderr  Verbosis ;
		if [ "${ArraySha[1]}" != "${ArraySha[2]}" ] ; then 
		 ArrayUpdateItem[${#ArrayUpdateItem[@]}]="${ArraySha[0]}";
		 StrMsg=${ArrayMsg[5]} ; 
		 StrMsg=${StrMsg//__FILE__/${ArraySha[0]}} ; 
   VerbMsg="${StrMsg}" VerbHeader="${__call_locality[1]}-DEBUG" VerbState=True VerbEvalForm=False VerbFormated=True VerbDev=/dev/stderr  Verbosis ;
		fi 
 StrASeg=${StrASeg/#${StrBSeg}} ;
 done 
 StrMsg=${ArrayMsg[6]} ;
 StrMsg=${StrMsg//__FILE__/${ArrayUpdateItem[@]}} ; 
	VerbMsg="${StrMsg}" VerbHeader="${__call_locality[1]}-DEBUG" VerbState=True VerbEvalForm=False VerbFormated=True VerbDev=/dev/stderr  Verbosis ;
 
 for (( intI=0 ; intI <= $(( ${#ArrayUpdateItem[@]}-1 )) ; intI++ )) ; do
  cp ${StrSourcePath}/${ArrayUpdateItem[${intI}]} ${StrDestinationPath} ; 
 done 

}

UTRSource=/usr/local/share/treeline/  \
UTRDestination=/home/maxiste/github/Treeline-encryption/TreeLine/source \
UTRIsDisplayDebug=False \
UTRIsDisplayCmd=False \
UpdateTreelineRepository ; 
