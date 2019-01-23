using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class HolderScript : MonoBehaviour {

    void Start()
    {
        float x1 = this.GetComponent<Renderer>().bounds.size.x;
        float x2 = ParameterScript.holderLength;
        float xScale = x2 / x1;

        float y1 = this.GetComponent<Renderer>().bounds.size.y;
        float y2 = ParameterScript.holderHeight;
        float yScale = y2 / y1;

        float z1 = this.GetComponent<Renderer>().bounds.size.z;
        float z2 = ParameterScript.holderRealWidth;
        float zScale = z2 / z1;

        MeshFilter meshf = this.GetComponent<MeshFilter>();
        Mesh mesh = meshf.mesh;
        Vector3[] newVecs = new Vector3[mesh.vertices.Length];
        Vector3[] oldVecs = mesh.vertices;
        for (int i = 0; i < oldVecs.Length; i++)
        {
            newVecs[i].Set(oldVecs[i].x * xScale, oldVecs[i].y * yScale, oldVecs[i].z * zScale);
        }
        mesh.vertices = newVecs;
        mesh.RecalculateBounds();
    }
}
