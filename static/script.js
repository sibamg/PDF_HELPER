let file_input=document.getElementById("file");

file_input.addEventListener("onchange",()=>{
    console.log("file iploaded")
    console.log(file_input.files);

})

//clearing user input
let clear=document.getElementById("clear")
clear.addEventListener('click',()=>{
    let q=document.getElementById("query")
    q.value=""
})
document.addEventListener('DOMContentLoaded',()=>{
    let buttons=document.querySelectorAll(".delete-chat")
    console.log(buttons);
    buttons.forEach((ele)=>{
        ele.addEventListener('click',function(){
            let button_id=this.getAttribute('data-id');
            console.log(button_id)
        fetch(`/delete/${button_id}`,{
            method:'POST',
        
        }).then(response=>response.json()).then(data=>{
            if(data.success){
                let chat=document.getElementById(`${button_id}`);
                console.log(chat)
                chat.remove();
            }
            else{
                console.log("errorr");
            }
        })
        
        })
    })
})