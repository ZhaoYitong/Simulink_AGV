using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class ThirdCamera : MonoBehaviour {

    public GameObject player;

    private Transform init_trans;
    private TaskManager task_manager;
    private Vector3 offset;
    private KeyCode currentKey;

	void Start () {
        init_trans = transform;
        GameObject tm = GameObject.Find("TaskManager");
        task_manager = tm.GetComponent<TaskManager>();
        offset = player.transform.position - this.transform.position;
        currentKey = KeyCode.Space;
	}
	
	// Update is called once per frame
	void Update () {
		if (Input.anyKeyDown)
        {
            Event e = Event.current;
            if (e.isKey)
            {
                currentKey = e.keyCode;
            }
        }
        int num_agv = task_manager.m_AGVs.Length;
        int cur_key = -1;
        try
        {
            cur_key = int.Parse(currentKey.ToString());
        }
        catch
        {

        }
        if (cur_key >= 0 && cur_key <= 9)
        {
            player = task_manager.m_AGVs[cur_key].m_Instance;
            transform.position = Vector3.Lerp(transform.position, player.transform.position - offset, Time.deltaTime * 20);
            Quaternion rotation = Quaternion.LookRotation(player.transform.position - transform.position);
            transform.rotation = Quaternion.Slerp(transform.rotation, rotation, Time.deltaTime * 12f);
        }
        if (Input.GetKeyDown("r"))
        {
            transform.position = init_trans.position;
            transform.rotation = init_trans.rotation;
        }
	}
}
