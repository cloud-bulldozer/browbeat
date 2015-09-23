#
# This code will increment by 10
# @author Joe Talerico <jtaleric@redhat.com>
#
RALLY_JSON="nova/nova-boot-list.json"
EXPECTED_SUCCESS="90"
REPEAT=3
INCREMENT=10
TIMESTAMP=$(date +%s)·
mkdir -p run-${REPEAT}

while [[ $REPEAT -gt 0 ]] ; do·
 RUN=true
 while $RUN ; do
  CONCURRENCY=`cat ${RALLY_JSON} | grep concurrency | awk '{print $2}'`
  echo "Current number of guests launching : ${CONCURRENCY}"
  RALLY_RESULT=$(rally task start ${RALLY_JSON})
  TASK=$(echo "${RALLY_RESULT}" | grep Task | grep finished | awk '{print substr($2,0,length($2)-1)}')
  RUN_RESULT=$(echo "${RALLY_RESULT}" | grep total | awk '{print $16}')
  echo "     Task : ${TASK}"
  echo "     Result : ${RUN_RESULT}"
  rally task report ${TASK} --out run-${REPEAT}/${TASK}.html
  rally task results ${TASK} > run-${REPEAT}/${TASK}.json

  SUCCESS_RATE=$(echo "${RUN_RESULT}" | awk -F. '{ print $1 }')

  if [ "${SUCCESS_RATE}" -ge "${EXPECTED_SUCCESS}" ] ; then
   NEW_CON=$(echo "`cat ${RALLY_JSON} | grep concurrency | awk '{print $2}'`+${INCREMENT}" | bc)
   sed -i "s/\"times\"\:.*$/\"times\"\: ${NEW_CON},/g" ${RALLY_JSON}
   sed -i "s/\"concurrency\"\:.*$/\"concurrency\"\: ${NEW_CON}/g" ${RALLY_JSON}
  else
   RUN=false
   sed -i "s/\"times\"\:.*$/\"times\"\: 10,/g" ${RALLY_JSON}
   sed -i "s/\"concurrency\"\:.*$/\"concurrency\"\: 10/g" ${RALLY_JSON}
  fi
  sleep 60
 done
 let REPEAT-=1
done
